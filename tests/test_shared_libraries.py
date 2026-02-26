import os
import sys
import importlib
import importlib.util
import pytest
import ctypes
import subprocess
from pathlib import Path

# The single shared library exposing all run_* functions
LIBRARY_NAME = "libloom-python-plugin"
PLUGIN_MODULE = "loom"  # pybind11 module name as imported in Python

# Functions expected to be exposed by the plugin
EXPECTED_FUNCTIONS = ["run_loom", "run_octi", "run_topo", "run_transitmap"]

# Define the directory containing the example JSON files
EXAMPLES_DIR = "src/loom/examples/"

# Define the output directory for the results
OUTPUT_DIR = "output/"

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# repo root
root = Path(__file__).resolve().parent.parent

# lib dir
lib_dir = root / "src/loom/lib"

# preload the .so with RTLD_GLOBAL so all symbols are available
if lib_dir.exists():
    sys.path.insert(0, str(lib_dir))
    for so in sorted(lib_dir.glob("*.so")):
        try:
            ctypes.CDLL(str(so), mode=os.RTLD_NOW | os.RTLD_GLOBAL)
        except Exception as e:
            print(f"Warning: Failed to load {so} with RTLD_GLOBAL: {e}")


@pytest.fixture(scope="module")
def lib_path():
    """Find the libloom-python-plugin.so path."""
    try:
        return next(root.rglob(f"{LIBRARY_NAME}*.so"))
    except StopIteration:
        pytest.fail(f"{LIBRARY_NAME}.so not found under {root}")


def test_shared_library_symbols(lib_path):
    """Test that the plugin .so loads without undefined symbol errors."""
    try:
        ctypes.CDLL(str(lib_path), mode=os.RTLD_NOW | os.RTLD_GLOBAL)
    except OSError as e:
        pytest.fail(f"Failed to load {lib_path} due to missing symbols: {e}")


def test_shared_library_dependencies(lib_path):
    """Test that all runtime dependencies of the plugin .so are satisfied (ldd)."""
    result = subprocess.run(
        ["ldd", str(lib_path)],
        capture_output=True,
        text=True,
    )
    missing = [
        line.strip()
        for line in result.stdout.splitlines()
        if "not found" in line
    ]
    assert missing == [], f"{LIBRARY_NAME} has missing dependencies:\n" + "\n".join(missing)


@pytest.mark.parametrize("fn_name", EXPECTED_FUNCTIONS)
def test_plugin_exposes_run_functions(lib_path, fn_name):
    """Test that the plugin can be imported and exposes all run_* functions."""
    spec = importlib.util.spec_from_file_location(PLUGIN_MODULE, str(lib_path))
    if spec is None:
        pytest.fail(f"Could not create spec from {lib_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert hasattr(mod, fn_name), f"{PLUGIN_MODULE} does not expose '{fn_name}'"
    assert callable(getattr(mod, fn_name)), f"{PLUGIN_MODULE}.{fn_name} is not callable"