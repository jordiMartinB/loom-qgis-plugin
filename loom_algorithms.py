import json
from pathlib import Path

from PyQt5.QtCore import QVariant

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterString,
    QgsProcessingOutputVectorLayer,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsField,
    QgsPointXY,
    QgsWkbTypes,
)

from wrapper import run_topo, run_loom, run_octi


# ---------------------------------------------------------------------------
# QVariant → Python native converter
# ---------------------------------------------------------------------------

def _to_python_native(val):
    """Recursively convert QGIS/Qt values to JSON-serialisable Python types.

    Uses a type-name check rather than isinstance so that the function works
    even when PyQt5 resolves QVariant differently across QGIS builds.
    """
    # Already primitive
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return val
    if isinstance(val, str):
        return val

    # QVariant (NULL or wrapped value) ─ identified by class name to be safe
    if type(val).__name__ == 'QVariant':
        try:
            if val.isNull():
                return None
            unwrapped = val.toPyObject() if hasattr(val, 'toPyObject') else val.value()
            # Guard against toPyObject() returning QVariant again
            if type(unwrapped).__name__ == 'QVariant':
                return None
            return _to_python_native(unwrapped)
        except Exception:
            try:
                return str(val.toString()) if hasattr(val, 'toString') else None
            except Exception:
                return None

    # Containers
    if isinstance(val, list):
        return [_to_python_native(x) for x in val]
    if isinstance(val, dict):
        return {str(k): _to_python_native(v) for k, v in val.items()}

    # Fallback for any other non-serialisable type
    return str(val)


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
# Base class and pipeline algorithms
# ---------------------------------------------------------------------------

class _LoomBaseAlgorithm(QgsProcessingAlgorithm):

    INPUT_NODES  = "INPUT_NODES"
    INPUT_EDGES  = "INPUT_EDGES"
    CONFIG       = "CONFIG"
    OUTPUT_NODES = "OUTPUT_NODES"
    OUTPUT_EDGES = "OUTPUT_EDGES"

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
            QgsProcessingParameterVectorLayer(
                self.INPUT_NODES,
                "Nodes / stops layer (points)",
                types=[QgsWkbTypes.PointGeometry],
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_EDGES,
                "Edges layer (lines)",
                types=[QgsWkbTypes.LineGeometry],
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
        self.addOutput(QgsProcessingOutputVectorLayer(self.OUTPUT_NODES, "Nodes / stops layer"))
        self.addOutput(QgsProcessingOutputVectorLayer(self.OUTPUT_EDGES, "Edges layer"))

    def _run(self, graph_json: str, config_json: str) -> str:
        raise NotImplementedError

    @staticmethod
    def _layer_to_geojson_features(layer: QgsVectorLayer) -> list:
        """Convert all features in a QgsVectorLayer to GeoJSON feature dicts.

        Field values that look like JSON (objects / arrays) are parsed back so
        nested structures (e.g. the ``lines`` array on edges) survive a
        round-trip through QGIS memory layers unchanged.
        """
        features = []
        fields = [f.name() for f in layer.fields()]
        for qf in layer.getFeatures():
            props = {}
            for name in fields:
                raw = _to_python_native(qf[name])
                # Parse back JSON-encoded strings (e.g. the ``lines`` array)
                if isinstance(raw, str):
                    stripped = raw.strip()
                    if stripped and stripped[0] in ("{", "["):
                        try:
                            raw = json.loads(stripped)
                        except json.JSONDecodeError:
                            pass
                # Do not include null values in the props dict.  The C++
                # loom backend accesses every optional field via .count() or
                # .find() first, so a missing key is handled gracefully.
                # A present-but-null JSON value causes type_error.302 on
                # scalar fields (.get<std::string>() on null) and a different
                # type error on array/object fields (range-for over a null or
                # empty-string JSON value).
                if raw is None:
                    continue
                props[name] = raw

            geom_json = json.loads(qf.geometry().asJson())
            # Skip features whose geometry is null – the C++ loom backend
            # cannot handle GeoJSON features with a null geometry field and
            # will raise json.exception.type_error.302.
            if geom_json is None:
                continue
            features.append({
                "type": "Feature",
                "properties": props,
                "geometry": geom_json,
            })
        return features

    @staticmethod
    def _make_layer(geom_type: str, geojson_features: list, name: str) -> QgsVectorLayer:
        """Create an in-memory QgsVectorLayer from a list of GeoJSON feature dicts."""
        layer = QgsVectorLayer(f"{geom_type}?crs=EPSG:4326", name, "memory")
        pr = layer.dataProvider()

        # Collect all property keys (preserve first-seen order)
        seen: set = set()
        ordered_keys: list = []
        for f in geojson_features:
            for k in (f.get("properties") or {}).keys():
                if k not in seen:
                    ordered_keys.append(k)
                    seen.add(k)

        pr.addAttributes([QgsField(k, QVariant.String) for k in ordered_keys])
        layer.updateFields()

        qgs_feats = []
        for f in geojson_features:
            qf = QgsFeature(layer.fields())

            # Properties
            for k, v in (f.get("properties") or {}).items():
                if isinstance(v, (dict, list)):
                    v = json.dumps(v)
                # Never assign None to a QGIS field – it becomes a NULL
                # QVariant which round-trips back as a JSON null and causes
                # json.exception.type_error.302 in the C++ backend.
                qf[k] = str(v) if v is not None else ""

            # Geometry
            geom_obj = f.get("geometry") or {}
            gtype = geom_obj.get("type", "")
            coords = geom_obj.get("coordinates", [])
            if gtype == "Point":
                qf.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(coords[0], coords[1])))
            elif gtype == "LineString":
                qf.setGeometry(QgsGeometry.fromPolylineXY(
                    [QgsPointXY(x, y) for x, y in coords]
                ))
            elif gtype == "MultiLineString":
                qf.setGeometry(QgsGeometry.fromMultiPolylineXY(
                    [[QgsPointXY(x, y) for x, y in part] for part in coords]
                ))

            qgs_feats.append(qf)

        pr.addFeatures(qgs_feats)
        layer.updateExtents()
        return layer

    def processAlgorithm(self, parameters, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        nodes_layer = self.parameterAsVectorLayer(parameters, self.INPUT_NODES, context)
        edges_layer = self.parameterAsVectorLayer(parameters, self.INPUT_EDGES, context)
        config_json = self.parameterAsString(parameters, self.CONFIG, context)
        if not config_json or not config_json.strip():
            config_json = "{}"

        feedback.pushInfo(f"Converting input layers to GeoJSON …")
        node_feats = self._layer_to_geojson_features(nodes_layer)
        edge_feats = self._layer_to_geojson_features(edges_layer)
        graph_json = json.dumps(
            {
                "type": "FeatureCollection",
                "features": node_feats + edge_feats,
            },
            default=_to_python_native,
        )
        feedback.pushInfo(
            f"Input: {len(node_feats)} nodes, {len(edge_feats)} edges. "
            f"Running {self.displayName()} …"
        )

        result_json = self._run(graph_json, config_json)

        fc = json.loads(result_json)
        all_features = fc.get("features", [])

        point_feats = [f for f in all_features if f.get("geometry", {}).get("type") == "Point"]
        line_feats  = [f for f in all_features
                       if f.get("geometry", {}).get("type") in ("LineString", "MultiLineString")]

        feedback.pushInfo(f"Building layers: {len(point_feats)} nodes, {len(line_feats)} edges.")

        nodes_layer = self._make_layer("Point",      point_feats, f"{self.displayName()} – Nodes")
        edges_layer = self._make_layer("LineString", line_feats,  f"{self.displayName()} – Edges")

        context.temporaryLayerStore().addMapLayer(nodes_layer)
        context.temporaryLayerStore().addMapLayer(edges_layer)
        context.addLayerToLoadOnCompletion(
            nodes_layer.id(),
            QgsProcessingContext.LayerDetails(
                f"{self.displayName()} – Nodes", context.project(), self.OUTPUT_NODES
            ),
        )
        context.addLayerToLoadOnCompletion(
            edges_layer.id(),
            QgsProcessingContext.LayerDetails(
                f"{self.displayName()} – Edges", context.project(), self.OUTPUT_EDGES
            ),
        )

        return {self.OUTPUT_NODES: nodes_layer.id(), self.OUTPUT_EDGES: edges_layer.id()}


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


# Note: `run_transitmap` was removed from the Python API; transitmap
# rendering is no longer exposed as a processing algorithm.
