import os
import subprocess
import sys
from pathlib import Path

import pybind11
from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class CMakeExtension(Extension):
    def __init__(self, name: str, source_dir: str = "."):
        super().__init__(name, sources=[])
        self.source_dir = Path(source_dir).resolve()


class CMakeBuild(build_ext):
    def build_extension(self, ext: CMakeExtension):
        build_type = os.environ.get("CMAKE_BUILD_TYPE", "Release")
        ext_dir = Path(self.get_ext_fullpath(ext.name)).parent.resolve()

        python_exe = Path(sys.executable).resolve()
        python_root = Path(sys.base_prefix).resolve()

        ver = f"{sys.version_info.major}{sys.version_info.minor}"

        # Search multiple candidate locations for python*.lib
        lib_candidates = [
            python_root / "libs" / f"python{ver}.lib",
            python_root / "Libs" / f"python{ver}.lib",
            python_root.parent / "libs" / f"python{ver}.lib",
            python_root.parent / "Libs" / f"python{ver}.lib",
        ]

        # Also search via glob in case location varies
        python_lib = None
        for candidate in lib_candidates:
            if candidate.exists():
                python_lib = candidate
                break

        if python_lib is None:
            # Try a glob search under base_prefix and its parent
            for search_root in [python_root, python_root.parent]:
                found = list(search_root.rglob(f"python{ver}.lib"))
                if found:
                    python_lib = found[0]
                    break

        cmake_args = [
            f"-Dpybind11_DIR={pybind11.get_cmake_dir()}",
            f"-DCMAKE_BUILD_TYPE={build_type}",
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={ext_dir}",
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_RELEASE={ext_dir}",
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_DEBUG={ext_dir}",
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_RELWITHDEBINFO={ext_dir}",
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_MINSIZEREL={ext_dir}",
            f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY={ext_dir}",
            f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE={ext_dir}",
            f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG={ext_dir}",
            f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY_RELWITHDEBINFO={ext_dir}",
            f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY_MINSIZEREL={ext_dir}",
            f"-DPYTHON_EXECUTABLE={python_exe}",
            f"-DPython3_EXECUTABLE={python_exe}",
            f"-DPython3_ROOT_DIR={python_root}",
            "-DPython3_FIND_STRATEGY=LOCATION",
            "-DPython3_FIND_REGISTRY=NEVER",
        ]

        if python_lib and python_lib.exists():
            cmake_args.append(f"-DPython3_LIBRARY={python_lib}")
            print(f"Using Python lib: {python_lib}")
        else:
            print(f"WARNING: python{ver}.lib not found, linker may fail")

        # Honour VCPKG on Windows
        vcpkg_root = os.environ.get("VCPKG_ROOT")
        if vcpkg_root:
            cmake_args.append(
                f"-DCMAKE_TOOLCHAIN_FILE={vcpkg_root}/scripts/buildsystems/vcpkg.cmake"
            )

        # Honour compiler launchers (ccache / sccache) if set in the environment
        for var in ("CMAKE_C_COMPILER_LAUNCHER", "CMAKE_CXX_COMPILER_LAUNCHER"):
            val = os.environ.get(var)
            if val:
                cmake_args.append(f"-D{var}={val}")

        # Use Ninja on Windows so CMAKE_C/CXX_COMPILER_LAUNCHER is honoured
        # (the default Visual Studio generator silently ignores launcher vars)
        if sys.platform == "win32":
            cmake_args += ["-G", "Ninja"]

        build_dir = Path(self.build_temp) / ext.name
        build_dir.mkdir(parents=True, exist_ok=True)

        # Strip Python-root env vars injected by CI (e.g. actions/setup-python).
        # Without this, CMake's FindPython3 and pybind11's internal FindPython
        # see Python3_ROOT_DIR / Python_ROOT_DIR pointing at the *host* Python
        # (e.g. 3.12) in the runner environment and select that interpreter
        # instead of the cibuildwheel-managed one, causing every .pyd to be
        # tagged cp312 regardless of the target Python version.
        _PURGE_VARS = {"Python3_ROOT_DIR", "Python_ROOT_DIR", "Python2_ROOT_DIR"}
        cmake_env = {k: v for k, v in os.environ.items() if k not in _PURGE_VARS}

        subprocess.run(
            ["cmake", str(ext.source_dir), *cmake_args],
            cwd=build_dir, check=True, env=cmake_env,
        )
        subprocess.run(
            ["cmake", "--build", ".", "--config", build_type, "--parallel"],
            cwd=build_dir, check=True, env=cmake_env,
        )


setup(
    name="loom-python-plugin",
    version="0.1.0",
    ext_modules=[CMakeExtension("loom", source_dir="src/loom")],
    cmdclass={"build_ext": CMakeBuild},
    zip_safe=False,
)
