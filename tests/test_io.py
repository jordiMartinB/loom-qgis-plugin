import os
import sys
import json
import importlib
import tempfile
from pathlib import Path
import unittest

# Define the shared libraries to test
MODULES = ["loom_python", "octi_python", "topo_python"]

# Define the directory containing the example JSON files
EXAMPLES_DIR = "src/loom/examples/"

# Define the output directory for the results
OUTPUT_DIR = "output/"

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
                module = importlib.import_module(module_name)

                # Pass the JSON content as a single string in a list to the main function
                result = module.main([json_content])  # Wrap json_content in a list

                # Save the output to a corresponding *-out.json file
                output_filename = f"{base_name}-{module_name}-out.json"
                output_path = os.path.join(OUTPUT_DIR, output_filename)
                with open(output_path, "w") as out_file:
                    json.dump(result, out_file, indent=4)

                print(f"Processed {filename} with {module_name}, output saved to {output_filename}")

            except Exception as e:
                print(f"Error processing {filename} with {module_name}: {e}")

if __name__ == "__main__":
    unittest.main()