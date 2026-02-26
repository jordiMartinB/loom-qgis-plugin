import os
import sys
import json
import importlib.util
import unittest
from pathlib import Path

# Define the directory containing the example JSON files
EXAMPLES_DIR = "src/loom/examples/"

# Define the output directory for the results
OUTPUT_DIR = "tests/output/"

# Define the configuration for each stage
CONFIG = {
    "topo": {
        "max-aggr-dist": 50,
        "write-stats": False,
        "no-infer-restrs": False,
        "infer-restr-max-dist": 50,
        "max-comp-dist": 10000,
        "sample-dist": 5,
        "max-length-dev": 500,
        "turn-restr-full-turn-angle": 0,
        "turn-restr-full-turn-pen": 0,
        "random-colors": False,
        "write-components": False,
        "write-components-path": "",
        "smooth": 0,
        "aggr-stats": False
    },
    "loom": {
        "no-untangle": False,
        "output-stats": False,
        "no-prune": False,
        "same-seg-cross-pen": 4.0,
        "diff-seg-cross-pen": 1.0,
        "sep-pen": 3.0,
        "in-stat-cross-pen-same-seg": 12.0,
        "in-stat-cross-pen-diff-seg": 3.0,
        "in-stat-sep-pen": 9.0,
        "ilp-num-threads": 0,
        "ilp-time-limit": 1.7976931348623157e+308,
        "ilp-solver": "gurobi",
        "optim-method": "comb-no-ilp",
        "optim-runs": 2,
        "dbg-output-path": ".",
        "output-optgraph": False,
        "write-stats": False,
        "from-dot": False
    },
    "octi": {
        "abortAfter": -1,
        "optimMode": "heur",
        "hananIters": 1,
        "heurLocSearchIters": 100,
        "ilpCacheThreshold": sys.float_info.max,
        "ilpCacheDir": ".",
        "obstaclePath": "",
        "deg2Heur": False,
        "enfGeoPen": 0.0,
        "maxGrDist": 3.0,
        "restrLocSearch": False,
        "edgeOrderMethod": "all",
        "baseGraphType": "octilinear",
        "pens": {
            "densityPen": 10.0,
            "verticalPen": 0.0,
            "horizontalPen": 0.0,
            "diagonalPen": 0.5,
            "p_0": 0.0,
            "p_135": 1.0,
            "p_90": 1.5,
            "p_45": 2.0,
            "ndMovePen": 0.5
        },
        "skipOnError": False,
        "retryOnError": False,
        "gridSize": "100%"
    },
    "transitmap": {
        "render-engine": "svg",
        "line-width": 20,
        "line-spacing": 10,
        "outline-width": 1,
        "render-dir-markers": False,
        "labels": False,
        "line-label-textsize": 40,
        "station-label-textsize": 60,
        "no-deg2-labels": False,
        "zoom": "14",
        "mvt-path": ".",
        "random-colors": False,
        "tight-stations": False,
        "no-render-stations": True,
        "no-render-node-connections": False,
        "render-node-fronts": True,
        "print-stats": False
    }
}

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# repo root
root = Path(__file__).resolve().parent.parent


class TestIO(unittest.TestCase):

    def _load_loom_module(self):
        """Load the loom pybind11 module by path."""
        lib_path = None
        try:
            lib_path = next(root.rglob("libloom-python-plugin.so"))
        except StopIteration:
            self.fail("libloom-python-plugin.so not found")
        
        spec = importlib.util.spec_from_file_location("loom", str(lib_path))
        if spec is None:
            self.fail(f"Could not create spec from {lib_path}")
        
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_io_pipeline(self):
        """Test the full loom pipeline: topo -> loom -> octi -> transitmap."""
        filename = "wien.json"
        input_path = os.path.join(EXAMPLES_DIR, filename)
        base_name = os.path.splitext(filename)[0]
        
        # Load the loom module
        loom_module = self._load_loom_module()

        # Read the input JSON
        with open(input_path, "r") as f:
            graph_json = f.read()

        # Stage 1: topo
        try:
            topo_config = json.dumps(CONFIG["topo"])
            topo_result = loom_module.run_topo([graph_json, topo_config])
            
            topo_output = os.path.join(OUTPUT_DIR, f"{base_name}-topo-out.json")
            with open(topo_output, "w") as out:
                out.write(topo_result)
            print(f"✓ topo output saved to {topo_output}")
        except Exception as e:
            self.fail(f"topo stage failed: {e}")

        # Stage 2: loom
        try:
            loom_config = json.dumps(CONFIG["loom"])
            loom_result = loom_module.run_loom([topo_result, loom_config])
            
            loom_output = os.path.join(OUTPUT_DIR, f"{base_name}-loom-out.json")
            with open(loom_output, "w") as out:
                out.write(loom_result)
            print(f"✓ loom output saved to {loom_output}")
        except Exception as e:
            self.fail(f"loom stage failed: {e}")

        # Stage 3: octi
        try:
            octi_config = json.dumps(CONFIG["octi"])
            octi_result = loom_module.run_octi([loom_result, octi_config])
            
            octi_output = os.path.join(OUTPUT_DIR, f"{base_name}-octi-out.json")
            with open(octi_output, "w") as out:
                out.write(octi_result)
            print(f"✓ octi output saved to {octi_output}")
        except Exception as e:
            self.fail(f"octi stage failed: {e}")

        # Stage 4: transitmap
        try:
            transitmap_config = json.dumps(CONFIG["transitmap"])
            transitmap_result = loom_module.run_transitmap([octi_result, transitmap_config])
            
            transitmap_output = os.path.join(OUTPUT_DIR, f"{base_name}-transitmap-out.svg")
            with open(transitmap_output, "w") as out:
                out.write(transitmap_result)
            print(f"✓ transitmap output saved to {transitmap_output}")
        except Exception as e:
            self.fail(f"transitmap stage failed: {e}")


if __name__ == "__main__":
    unittest.main()