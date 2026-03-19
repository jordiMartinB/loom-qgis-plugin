#!/usr/bin/env python3
"""
validate_geojson_linegraph.py

Validate a GeoJSON stream (FeatureCollection or array of features) to check
that it conforms to the expectations in LineGraph::readFromGeoJson
(src/loom/src/shared/linegraph/LineGraph.cpp).

Run:
  cat data.geojson | python3 scripts/validate_geojson_linegraph.py
or:
  python3 scripts/validate_geojson_linegraph.py data.geojson

The script performs a best-effort validation based on the C++ logic:
- Point features:
  - must have "geometry.type" == "Point"
  - "geometry.coordinates" must be an array with at least 2 numeric items
  - if "properties.id" is present it must be a JSON string (C++ code calls get<string>())
  - "properties.component" (if present) must be numeric
  - "properties.not_serving" (if present) must be array of strings
  - "properties.excluded_conn" (if present) must be array of objects, each having
    "line", "node_from", "node_to" as strings
- LineString features:
  - must have "geometry.type" == "LineString"
  - "geometry.coordinates" must be an array of coordinate arrays with at least 2 numeric items each
  - "properties.from"/"properties.to" (if present and not null) must be strings
  - "properties.component" (if present) must be numeric
  - "properties.dontcontract" (if present) must be numeric (C++ checks is_number and reads as int)
  - if "from"/"to" reference an existing point id, that id must be defined by a Point feature
  - self-edges where resolved from==to are flagged (C++ drops them)
- "id" generation: if a Point has no id property the code in C++ generates an id using:
    "<int(x)>|<int(y)>"
  This script replicates that generation using the raw coordinates in the feature (no reprojection).
  If your input uses lat/lng and LineGraph expects web-mercator, you can pass --web-merc to indicate
  coordinates are already web-mercator. If you don't pass it and coordinates need projection,
  the generated ids may not match what the C++ code produces when webMercCoords=false.

Exit code:
- 0 if no errors detected (warnings are printed but non-fatal)
- 2 if fatal validation errors are found
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
def is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def int_cast_trunc(x: float) -> int:
    # C++ static_cast<int>(double) truncates toward zero
    return int(x)


def gen_point_id_from_coords(coords: List[float]) -> str:
    # replicate C++ id generation: "<int(x)>|<int(y)>"
    x = coords[0]
    y = coords[1]
    return f"{int_cast_trunc(x)}|{int_cast_trunc(y)}"


# -----------------------------------------------------------------------------
# Validator
# -----------------------------------------------------------------------------
class Validator:
    def __init__(self, features: List[Dict[str, Any]], web_merc: bool = True) -> None:
        self.features = features
        self.web_merc = web_merc
        self.errors: List[str] = []
        self.warnings: List[str] = []
        # id_map: id -> (feature_index, coords)
        self.id_map: Dict[str, Tuple[int, List[float]]] = {}

    def _err(self, msg: str) -> None:
        self.errors.append(msg)

    def _warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def validate(self) -> None:
        # First pass: collect Point nodes (idMap)
        for idx, feat in enumerate(self.features):
            if not isinstance(feat, dict):
                self._err(f"feature[{idx}] is not an object")
                continue
            props = feat.get("properties")
            geom = feat.get("geometry")
            if geom is None:
                self._err(f"feature[{idx}]: missing 'geometry'")
                continue
            gtype = geom.get("type")
            if gtype == "Point":
                self._validate_point(idx, props, geom)

        # Second pass: validate LineString edges
        for idx, feat in enumerate(self.features):
            props = feat.get("properties")
            geom = feat.get("geometry")
            if geom is None:
                # already reported in first pass if needed
                continue
            gtype = geom.get("type")
            if gtype == "LineString":
                self._validate_linestring(idx, props, geom)

        # Third pass: node exceptions (not_serving, excluded_conn)
        for idx, feat in enumerate(self.features):
            props = feat.get("properties")
            geom = feat.get("geometry")
            if geom is None:
                continue
            gtype = geom.get("type")
            if gtype == "Point":
                self._validate_point_exceptions(idx, props, geom)

    def _validate_point(self, idx: int, props: Any, geom: Any) -> None:
        # properties should be an object (but code will accept absent)
        if props is None:
            props = {}
        elif not isinstance(props, dict):
            self._err(f"feature[{idx}] Point: 'properties' must be an object")

        coords = geom.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            self._err(
                f"feature[{idx}] Point: 'geometry.coordinates' must be an array of at least 2 numbers"
            )
            return
        if not (is_number(coords[0]) and is_number(coords[1])):
            self._err(
                f"feature[{idx}] Point: 'geometry.coordinates' must contain numeric x,y"
            )
            return

        # props.id must be string if present
        if props is not None and "id" in props:
            if not isinstance(props["id"], str):
                self._err(
                    f"feature[{idx}] Point: properties.id must be a string (C++ calls get<string>())"
                )
                # do not return; continue with generated id fallback below

        # component if present must be numeric
        if props is not None and "component" in props:
            if not is_number(props["component"]):
                self._err(f"feature[{idx}] Point: properties.component must be numeric")

        # compute ID the same way C++ would (no reprojection here)
        id_val = None
        if props is not None and "id" in props and isinstance(props["id"], str):
            id_val = props["id"]
        else:
            id_val = gen_point_id_from_coords(coords)

        # duplicate ids are ignored by C++ (it 'continue's) - we warn
        if id_val in self.id_map:
            self._warn(
                f"feature[{idx}] Point: id '{id_val}' already defined by feature[{self.id_map[id_val][0]}], duplicates will be ignored"
            )
        else:
            self.id_map[id_val] = (idx, coords)

    def _validate_linestring(self, idx: int, props: Any, geom: Any) -> None:
        if props is None:
            props = {}
        elif not isinstance(props, dict):
            self._err(f"feature[{idx}] LineString: 'properties' must be an object")

        coords = geom.get("coordinates")
        if coords is None:
            self._warn(
                f"feature[{idx}] LineString: 'geometry.coordinates' is null; C++ will skip this feature"
            )
            return
        if not isinstance(coords, list) or len(coords) == 0:
            self._err(
                f"feature[{idx}] LineString: 'geometry.coordinates' must be a non-empty array of coordinate arrays"
            )
            return

        # Build polyline coords and validate items
        for j, c in enumerate(coords):
            if not isinstance(c, list) or len(c) < 2:
                self._err(
                    f"feature[{idx}] LineString: coordinate[{j}] must be an array of at least 2 numbers"
                )
            else:
                if not (is_number(c[0]) and is_number(c[1])):
                    self._err(
                        f"feature[{idx}] LineString: coordinate[{j}] must contain numeric x,y"
                    )

        # component if present must be numeric
        if props is not None and "component" in props:
            if not is_number(props["component"]):
                self._err(
                    f"feature[{idx}] LineString: properties.component must be numeric"
                )

        # from/to handling: if present and not null must be string
        from_prop = props.get("from") if isinstance(props, dict) else None
        to_prop = props.get("to") if isinstance(props, dict) else None

        def resolve_endpoint(prop_val, which: str) -> Tuple[str, bool]:
            """
            Returns (id_string, existed_in_id_map)
            If prop_val is None or prop_val is JSON null -> treated as empty string in C++.
            If prop_val is non-empty string -> return it.
            If empty string -> C++ generates from coords: "<int(front.x)>|<int(front.y)>"
            If prop present but not string nor null -> validation error and return ("", False)
            """
            if prop_val is None:
                return ("", False)
            # JSON null maps to None in Python; but some parsers may use None for null; treat that as empty
            if prop_val is None:
                return ("", False)
            # If explicitly null in JSON, we've seen it as None; treat as empty
            # If property is present and is not a string, that's an error in C++ (get<string>() would throw)
            if isinstance(prop_val, str):
                idstr = prop_val
                existed = idstr in self.id_map
                return (idstr, existed)
            else:
                self._err(
                    f"feature[{idx}] LineString: properties.{which} must be a string or null"
                )
                return ("", False)

        # Resolve 'from'
        from_id, from_exists = resolve_endpoint(from_prop, "from")
        # Resolve 'to'
        to_id, to_exists = resolve_endpoint(to_prop, "to")

        # If from/to are empty strings, C++ generates ids from front/back coords
        if not from_id:
            if len(coords) >= 1:
                generated_from = gen_point_id_from_coords(coords[0])
                # C++ will insert a new node idMap[generated_from] = addNd(...) if not present
                # So it's not an error if it's missing. We still warn if it doesn't exist so user is aware.
                if generated_from not in self.id_map:
                    self._warn(
                        f"feature[{idx}] LineString: 'from' empty -> generated id '{generated_from}' does not match any Point feature (C++ will create a node)"
                    )
                from_id = generated_from
                from_exists = generated_from in self.id_map
            else:
                self._err(
                    f"feature[{idx}] LineString: cannot generate 'from' id from empty coords"
                )

        if not to_id:
            if len(coords) >= 1:
                generated_to = gen_point_id_from_coords(coords[-1])
                if generated_to not in self.id_map:
                    self._warn(
                        f"feature[{idx}] LineString: 'to' empty -> generated id '{generated_to}' does not match any Point feature (C++ will create a node)"
                    )
                to_id = generated_to
                to_exists = generated_to in self.id_map
            else:
                self._err(
                    f"feature[{idx}] LineString: cannot generate 'to' id from empty coords"
                )

        # If from/to provided but do not exist in id_map => C++ logs error and continues (edge dropped)
        if (
            props is not None
            and "from" in props
            and isinstance(props["from"], str)
            and (from_id not in self.id_map)
        ):
            self._err(
                f"feature[{idx}] LineString: 'from' references id '{from_id}' which has no corresponding Point feature (edge will be skipped in C++)"
            )
        if (
            props is not None
            and "to" in props
            and isinstance(props["to"], str)
            and (to_id not in self.id_map)
        ):
            self._err(
                f"feature[{idx}] LineString: 'to' references id '{to_id}' which has no corresponding Point feature (edge will be skipped in C++)"
            )

        # If both resolve to same id, C++ drops self-edge
        if from_id and to_id and (from_id == to_id):
            self._warn(
                f"feature[{idx}] LineString: resolved 'from' and 'to' refer to the same node '{from_id}'; C++ will drop self-edges"
            )

        # dontcontract must be numeric if present (C++ checks is_number and get<int>())
        if props is not None and "dontcontract" in props:
            if not is_number(props["dontcontract"]):
                self._err(
                    f"feature[{idx}] LineString: properties.dontcontract must be numeric (C++ checks is_number and reads as int)"
                )

        # Note: extractLines(props, e, idMap) may remove edge if no lines found.
        # We cannot validate extractLines semantics here without further knowledge.

    def _validate_point_exceptions(self, idx: int, props: Any, geom: Any) -> None:
        # Validate not_serving and excluded_conn types and references
        if props is None or not isinstance(props, dict):
            return

        # find id for this point (must be one of those collected earlier)
        point_id = None
        if "id" in props and isinstance(props["id"], str):
            point_id = props["id"]
        else:
            coords = geom.get("coordinates")
            if (
                isinstance(coords, list)
                and len(coords) >= 2
                and is_number(coords[0])
                and is_number(coords[1])
            ):
                point_id = gen_point_id_from_coords(coords)
            else:
                # invalid coords already reported earlier
                return

        if point_id not in self.id_map:
            # C++ continues if idMap doesn't contain id
            return

        # not_serving: must be an array of strings
        if "not_serving" in props and props["not_serving"] is not None:
            ns = props["not_serving"]
            if not isinstance(ns, list):
                self._err(
                    f"feature[{idx}] Point: properties.not_serving must be an array"
                )
            else:
                for j, item in enumerate(ns):
                    if not isinstance(item, str):
                        self._err(
                            f"feature[{idx}] Point: properties.not_serving[{j}] must be a string (line id)"
                        )

        # excluded_conn: must be array of objects with line, node_from, node_to (strings)
        if "excluded_conn" in props and props["excluded_conn"] is not None:
            exc = props["excluded_conn"]
            if not isinstance(exc, list):
                self._err(
                    f"feature[{idx}] Point: properties.excluded_conn must be an array"
                )
            else:
                for j, item in enumerate(exc):
                    if not isinstance(item, dict):
                        self._err(
                            f"feature[{idx}] Point: properties.excluded_conn[{j}] must be an object"
                        )
                        continue
                    for key in ("line", "node_from", "node_to"):
                        if key not in item or not isinstance(item[key], str):
                            self._err(
                                f"feature[{idx}] Point: properties.excluded_conn[{j}].{key} must be a string"
                            )
                    # check referenced nodes exist in id_map
                    nid1 = item.get("node_from")
                    nid2 = item.get("node_to")
                    if isinstance(nid1, str) and nid1 not in self.id_map:
                        self._warn(
                            f"feature[{idx}] Point: excluded_conn[{j}] references node_from '{nid1}' which is not defined (C++ warns)"
                        )
                    if isinstance(nid2, str) and nid2 not in self.id_map:
                        self._warn(
                            f"feature[{idx}] Point: excluded_conn[{j}] references node_to '{nid2}' which is not defined (C++ warns)"
                        )


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def load_features_from_stream(fp) -> List[Dict[str, Any]]:
    data = json.load(fp)
    # if top-level is an object with "features" use that
    if (
        isinstance(data, dict)
        and "features" in data
        and isinstance(data["features"], list)
    ):
        return data["features"]
    # if top-level is already a list, assume it's the features array
    if isinstance(data, list):
        return data
    raise ValueError(
        "Input JSON must be either a FeatureCollection object with a 'features' array or an array of features"
    )


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Validate GeoJSON stream for LineGraph expectations"
    )
    parser.add_argument(
        "file", nargs="?", help="GeoJSON file to validate (defaults to stdin)"
    )
    parser.add_argument(
        "--web-merc",
        dest="web_merc",
        action="store_true",
        help="treat coordinates as web-mercator (default: true)",
    )
    parser.add_argument(
        "--no-web-merc",
        dest="web_merc",
        action="store_false",
        help="treat coordinates as lat/lng (no reprojection is performed, ids may differ)",
    )
    parser.set_defaults(web_merc=True)
    args = parser.parse_args(argv[1:])

    try:
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                features = load_features_from_stream(f)
        else:
            features = load_features_from_stream(sys.stdin)
    except Exception as e:
        print(f"ERROR: failed to read input JSON: {e}", file=sys.stderr)
        return 2

    v = Validator(features, web_merc=args.web_merc)
    v.validate()

    # print results
    if v.errors:
        print("Validation errors:", file=sys.stderr)
        for e in v.errors:
            print(f"  - {e}", file=sys.stderr)
    if v.warnings:
        print("Validation warnings:", file=sys.stderr)
        for w in v.warnings:
            print(f"  - {w}", file=sys.stderr)

    if v.errors:
        print(
            f"\nResult: INVALID ({len(v.errors)} error(s), {len(v.warnings)} warning(s))",
            file=sys.stderr,
        )
        return 2
    else:
        print(f"Result: OK (no errors, {len(v.warnings)} warning(s))")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
