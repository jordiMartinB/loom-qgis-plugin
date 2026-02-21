import unittest
import importlib
import importlib.util
import os
import sys
from pathlib import Path
import ctypes

MODULES = ["loom_python", "octi_python", "topo_python"]

# Add repo dirs that contain the compiled .so modules to sys.path so imports succeed
root = Path(__file__).resolve().parent.parent

# Ensure lib/ from repo root is on sys.path and preload its .so files with RTLD_GLOBAL so symbols resolve
lib_dir = root / "lib"
if lib_dir.exists():
    sys.path.insert(0, str(lib_dir))
    for so in sorted(lib_dir.glob("*.so")):
        try:
            ctypes.CDLL(str(so), mode=os.RTLD_NOW | os.RTLD_GLOBAL)
        except OSError:
            pass

for pattern in [f"{m}*.so" for m in MODULES]:
    for p in root.rglob(pattern):
        sys.path.insert(0, str(p.parent))

class TestSharedLibraries(unittest.TestCase):

    def test_modules_have_specs_and_import(self):
        for name in MODULES:
            with self.subTest(module=name):
                spec = importlib.util.find_spec(name)
                if spec is None:
                    self.skipTest(f"{name} not available in import search path")
                try:
                    mod = importlib.import_module(name)
                    self.assertIsNotNone(mod)
                except ImportError as e:
                    self.fail(f"Failed to load {name} shared library: {e}")
                except Exception as e:
                    self.fail(f"Unexpected error while loading {name}: {e}")

    def test_modules_provide_files(self):
        for name in MODULES:
            with self.subTest(module=name):
                spec = importlib.util.find_spec(name)
                if spec is None:
                    self.skipTest(f"{name} spec not found")
                try:
                    mod = importlib.import_module(name)
                except ImportError as e:
                    self.skipTest(f"Cannot import {name}: {e}")
                except Exception as e:
                    self.skipTest(f"Unexpected error while importing {name}: {e}")
                file_path = getattr(mod, "__file__", None)
                self.assertIsNotNone(file_path, f"{name} has no __file__")
                self.assertTrue(os.path.exists(file_path), f"{name} __file__ does not exist: {file_path}")

    def test_shared_library_symbols(self):
        for name in MODULES:
            with self.subTest(module=name):
                try:
                    lib_path = next(root.rglob(f"{name}*.so"))
                    self.assertTrue(lib_path.exists(), f"{name} shared library not found")
                    ctypes.CDLL(str(lib_path), mode=os.RTLD_NOW | os.RTLD_GLOBAL)
                except StopIteration:
                    self.fail(f"{name} shared library not found in expected paths")
                except OSError as e:
                    self.fail(f"Failed to load {name} shared library due to missing symbols: {e}")

    def test_shared_library_dependencies(self):
        for name in MODULES:
            with self.subTest(module=name):
                try:
                    lib_path = next(root.rglob(f"{name}*.so"))
                    self.assertTrue(lib_path.exists(), f"{name} shared library not found")
                    output = os.popen(f"ldd {lib_path}").read()
                    self.assertNotIn("not found", output, f"{name} shared library has missing dependencies:\n{output}")
                except StopIteration:
                    self.fail(f"{name} shared library not found in expected paths")
                except Exception as e:
                    self.fail(f"Error while checking dependencies for {name}: {e}")

if __name__ == '__main__':
    unittest.main()