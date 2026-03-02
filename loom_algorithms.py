import json
from pathlib import Path

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingOutputString,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsWkbTypes,
    QgsJsonExporter,
)

from wrapper import run_topo, run_loom, run_octi, run_transitmap

# ---------------------------------------------------------------------------
# Load default configurations from algorithm_config.json (sits next to this
# file in the plugin directory).  Falls back to empty dicts if missing.
# ---------------------------------------------------------------------------
_CONFIG_PATH = Path(__file__).parent / "algorithm_config.json"
try:
    with _CONFIG_PATH.open(encoding="utf-8") as _f:
        _ALGORITHM_CONFIG: dict = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError):
    _ALGORITHM_CONFIG = {}


# ---------------------------------------------------------------------------
# Graph builder: converts two QGIS vector layers -> loom GeoJSON
# ---------------------------------------------------------------------------

class BuildGraphAlgorithm(QgsProcessingAlgorithm):
    """
    Build a loom-compatible GeoJSON FeatureCollection from a stops (point)
    layer and an edges (line) layer.

    Stop features become GeoJSON Points with properties:
        id, station_id, station_label

    Edge features become GeoJSON LineStrings with properties:
        id, from, to, lines  (lines is a list of {id, label, color})
    """

    STOPS           = "STOPS"
    STOP_ID         = "STOP_ID"
    STOP_LABEL      = "STOP_LABEL"
    EDGES           = "EDGES"
    EDGE_FROM       = "EDGE_FROM"
    EDGE_TO         = "EDGE_TO"
    EDGE_LINE_LABEL = "EDGE_LINE_LABEL"
    EDGE_LINE_COLOR = "EDGE_LINE_COLOR"
    OUTPUT          = "OUTPUT"

    def name(self)        -> str: return "build_graph"
    def displayName(self) -> str: return "Build Loom Graph"
    def group(self)       -> str: return "Loom"
    def groupId(self)     -> str: return "loom"

    def shortHelpString(self) -> str:
        return (
            "Convert a <b>stops</b> (point) layer and an <b>edges</b> (line) "
            "layer into a loom-compatible GeoJSON FeatureCollection. "
            "The output JSON can be fed directly into <i>Run Topo</i>."
        )

    def initAlgorithm(self, config=None):
        # --- Stops ----------------------------------------------------------
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.STOPS, "Stops layer",
            types=[QgsProcessingParameterVectorLayer.typeVectorPoint],
        ))
        self.addParameter(QgsProcessingParameterField(
            self.STOP_ID, "Stop ID field",
            parentLayerParameterName=self.STOPS,
            optional=False,
        ))
        self.addParameter(QgsProcessingParameterField(
            self.STOP_LABEL, "Stop label field",
            parentLayerParameterName=self.STOPS,
            optional=True,
        ))

        # --- Edges ----------------------------------------------------------
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.EDGES, "Edges layer",
            types=[QgsProcessingParameterVectorLayer.typeVectorLine],
        ))
        self.addParameter(QgsProcessingParameterField(
            self.EDGE_FROM, "Edge 'from' stop ID field",
            parentLayerParameterName=self.EDGES,
            optional=False,
        ))
        self.addParameter(QgsProcessingParameterField(
            self.EDGE_TO, "Edge 'to' stop ID field",
            parentLayerParameterName=self.EDGES,
            optional=False,
        ))
        self.addParameter(QgsProcessingParameterField(
            self.EDGE_LINE_LABEL, "Edge line label field (transit line name)",
            parentLayerParameterName=self.EDGES,
            optional=True,
        ))
        self.addParameter(QgsProcessingParameterField(
            self.EDGE_LINE_COLOR, "Edge line color field (hex, e.g. ff0000)",
            parentLayerParameterName=self.EDGES,
            optional=True,
        ))

        self.addOutput(QgsProcessingOutputString(self.OUTPUT, "Loom graph (GeoJSON)"))

    def processAlgorithm(self, parameters, context: QgsProcessingContext,
                         feedback: QgsProcessingFeedback):
        stops_layer  = self.parameterAsVectorLayer(parameters, self.STOPS,  context)
        edges_layer  = self.parameterAsVectorLayer(parameters, self.EDGES,  context)
        stop_id_fld  = self.parameterAsString(parameters, self.STOP_ID,         context)
        stop_lbl_fld = self.parameterAsString(parameters, self.STOP_LABEL,       context)
        from_fld     = self.parameterAsString(parameters, self.EDGE_FROM,        context)
        to_fld       = self.parameterAsString(parameters, self.EDGE_TO,          context)
        lbl_fld      = self.parameterAsString(parameters, self.EDGE_LINE_LABEL,  context)
        color_fld    = self.parameterAsString(parameters, self.EDGE_LINE_COLOR,  context)

        features = []

        # --- Stop (point) features ------------------------------------------
        feedback.pushInfo(f"Processing {stops_layer.featureCount()} stops …")
        for feat in stops_layer.getFeatures():
            geom = feat.geometry()
            if geom.isNull():
                continue
            pt = geom.asPoint()
            stop_id = str(feat[stop_id_fld])
            props = {
                "id": stop_id,
                "station_id": stop_id,
                "station_label": str(feat[stop_lbl_fld]) if stop_lbl_fld else stop_id,
            }
            features.append({
                "type": "Feature",
                "properties": props,
                "geometry": {"type": "Point", "coordinates": [pt.x(), pt.y()]},
            })

        # --- Edge (line) features -------------------------------------------
        feedback.pushInfo(f"Processing {edges_layer.featureCount()} edges …")
        for i, feat in enumerate(edges_layer.getFeatures()):
            geom = feat.geometry()
            if geom.isNull():
                continue

            edge_id = str(feat.id())
            from_id = str(feat[from_fld])
            to_id   = str(feat[to_fld])

            # Build lines list — support comma-separated values in a single field
            if lbl_fld:
                labels = [l.strip() for l in str(feat[lbl_fld]).split(",") if l.strip()]
                colors = []
                if color_fld:
                    raw_colors = str(feat[color_fld])
                    colors = [c.strip().lstrip("#") for c in raw_colors.split(",") if c.strip()]
                lines = [
                    {
                        "id": f"{edge_id}_{j}",
                        "label": labels[j] if j < len(labels) else "",
                        "color": colors[j] if j < len(colors) else "888888",
                    }
                    for j in range(len(labels))
                ]
            else:
                lines = []

            # Extract coordinates (handles MultiLineString too)
            coords = []
            if geom.isMultipart():
                for part in geom.asMultiPolyline():
                    for v in part:
                        coords.append([v.x(), v.y()])
            else:
                for v in geom.asPolyline():
                    coords.append([v.x(), v.y()])

            features.append({
                "type": "Feature",
                "properties": {"id": edge_id, "from": from_id, "to": to_id, "lines": lines},
                "geometry": {"type": "LineString", "coordinates": coords},
            })

        graph = {"type": "FeatureCollection", "features": features}
        result = json.dumps(graph)
        feedback.pushInfo(f"Built graph with {len(features)} features.")
        return {self.OUTPUT: result}

    def createInstance(self):
        return BuildGraphAlgorithm()


# ---------------------------------------------------------------------------
# Base class and pipeline algorithms
# ---------------------------------------------------------------------------

    INPUT = "INPUT"
    CONFIG = "CONFIG"
    OUTPUT = "OUTPUT"

    # Subclasses must set these
    _name: str = ""
    _display_name: str = ""
    _short_help: str = ""
    _config_key: str = ""  # key into _ALGORITHM_CONFIG

    def name(self) -> str:
        return self._name

    def displayName(self) -> str:
        return self._display_name

    def shortHelpString(self) -> str:
        return self._short_help

    def group(self) -> str:
        return "Loom"

    def groupId(self) -> str:
        return "loom"

    def initAlgorithm(self, config=None):
        default_cfg = _ALGORITHM_CONFIG.get(self._config_key, {})
        default_cfg_str = json.dumps(default_cfg, indent=2) if default_cfg else "{}"

        self.addParameter(
            QgsProcessingParameterString(
                self.INPUT,
                "Input graph (JSON)",
                multiLine=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.CONFIG,
                "Configuration (JSON)",
                multiLine=True,
                optional=True,
                defaultValue=default_cfg_str,
            )
        )
        self.addOutput(
            QgsProcessingOutputString(self.OUTPUT, "Output (JSON)")
        )

    def _run(self, graph_json: str, config_json: str) -> str:
        raise NotImplementedError

    def processAlgorithm(self, parameters, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        graph_json = self.parameterAsString(parameters, self.INPUT, context)
        config_json = self.parameterAsString(parameters, self.CONFIG, context)
        feedback.pushInfo(f"Running {self.displayName()} …")
        result = self._run(graph_json, config_json)
        return {self.OUTPUT: result}


# ---------------------------------------------------------------------------
# Concrete algorithms
# ---------------------------------------------------------------------------

class RunTopoAlgorithm(_LoomBaseAlgorithm):
    _name = "run_topo"
    _display_name = "Run Topo"
    _config_key = "topo"
    _short_help = (
        "Topologise a transit graph using the loom <i>topo</i> stage. "
        "Accepts a graph JSON and a configuration JSON, returns the "
        "topologised graph as JSON."
    )

    def _run(self, graph_json: str, config_json: str) -> str:
        return run_topo(graph_json, config_json)

    def createInstance(self):
        return RunTopoAlgorithm()


class RunLoomAlgorithm(_LoomBaseAlgorithm):
    _name = "run_loom"
    _display_name = "Run Loom"
    _config_key = "loom"
    _short_help = (
        "Optimise line ordering on a transit graph using the loom "
        "<i>loom</i> stage. Accepts a graph JSON and a configuration "
        "JSON, returns the ordered graph as JSON."
    )

    def _run(self, graph_json: str, config_json: str) -> str:
        return run_loom(graph_json, config_json)

    def createInstance(self):
        return RunLoomAlgorithm()


class RunOctiAlgorithm(_LoomBaseAlgorithm):
    _name = "run_octi"
    _display_name = "Run Octi"
    _config_key = "octi"
    _short_help = (
        "Compute an octilinear layout for a transit graph using the loom "
        "<i>octi</i> stage. Accepts a graph JSON and a configuration "
        "JSON, returns the laid-out graph as JSON."
    )

    def _run(self, graph_json: str, config_json: str) -> str:
        return run_octi(graph_json, config_json)

    def createInstance(self):
        return RunOctiAlgorithm()


class RunTransitMapAlgorithm(_LoomBaseAlgorithm):
    _name = "run_transitmap"
    _display_name = "Run TransitMap"
    _config_key = "transitmap"
    _short_help = (
        "Render a transit graph to SVG using the loom <i>transitmap</i> "
        "stage. Accepts a graph JSON and a configuration JSON, returns "
        "the rendered SVG as a string."
    )


    def _run(self, graph_json: str, config_json: str) -> str:
        return run_transitmap(graph_json, config_json)

    def createInstance(self):
        return RunTransitMapAlgorithm()
