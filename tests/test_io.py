import os
import sys
import json
import importlib
import unittest

# Define the shared libraries to test
MODULES = ["loom", "octi"]

# Define the directory containing the example JSON files
EXAMPLES_DIR = "src/loom/examples/"

# Define the output directory for the results
OUTPUT_DIR = "tests/output/"

# Define the configuration for Loom (if needed for the tests)
CONFIG_LOOM = {
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
    "ilp-time-limit": -1.0,
    "ilp-solver": "gurobi",
    "optim-method": "comb-no-ilp",
    "optim-runs": 1,
    "dbg-output-path": ".",
    "output-optgraph": False,
    "write-stats": False,
    "from-dot": False
  },
  "octi": {
    "abortAfter": 0,
    "optimMode": "heur",
    "hananIters": 1,
    "heurLocSearchIters": 100,
    "ilpCacheThreshold": "inf",
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
    "no-render-stations": False,
    "no-render-node-connections": False,
    "render-node-fronts": False,
    "print-stats": False
  }
}

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

class TestIO(unittest.TestCase):

    def test_io(self):
        # Only process the wien.json file
        filename = "wien.json"
        input_path = os.path.join(EXAMPLES_DIR, filename)
        base_name = os.path.splitext(filename)[0]
        
        # Add the directory containing the shared libraries to PYTHONPATH
        LIB_DIR = os.path.join(os.path.dirname(__file__), "../lib")
        sys.path.insert(0, LIB_DIR)

        # Read the content of the JSON file
        with open(input_path, "r") as f:
            json_content = f.read()

        # Test each shared library
        for module_name in MODULES:
            try:
                # Import the shared library
                module = importlib.import_module(f"{module_name}_python")

                # Pass the JSON content as a single string in a list to the main function
                result = module.run([json_content, json.dumps(CONFIG_LOOM[module_name])])  # Wrap json_content in a list

                # Save the output to a corresponding *-out.json file
                output_filename = f"{base_name}-{module_name}-out.json"
                output_path = os.path.join(OUTPUT_DIR, output_filename)
                with open(output_path, "w") as out_file:
                    out_file.write(result)

                print(f"Processed {filename} with {module_name}, output saved to {output_filename}")

            except Exception as e:
                # Fail the test if an exception occurs
                self.fail(f"Error processing {filename} with {module_name}: {e}")

if __name__ == "__main__":
    unittest.main()