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

        # Resolve the real Python root (not the venv).
        # In a cibuildwheel venv, sys.executable is <venv>/Scripts/python.exe
        # and the real install is the parent of the venv root.
        python_exe = Path(sys.executable).resolve()
        python_root = Path(sys.base_prefix).resolve()

        # On Windows, python*.lib lives in <real_root>/libs/, not in the venv.
        # Walk up from the venv root to find it.
        ver = f"{sys.version_info.major}{sys.version_info.minor}"
        python_lib = python_root / "libs" / f"python{ver}.lib"
        if not python_lib.exists():
            # venv base_prefix doesn't have libs/ — try the real install root
            # cibuildwheel places the real Python one level above the venv
            real_root = python_root.parent
            candidate = real_root / "libs" / f"python{ver}.lib"
            if candidate.exists():
                python_root = real_root
                python_lib = candidate

        cmake_args = [
            f"-Dpybind11_DIR={pybind11.get_cmake_dir()}",
            f"-DCMAKE_BUILD_TYPE={build_type}",
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={ext_dir}",
            f"-DPYTHON_EXECUTABLE={python_exe}",
            f"-DPython3_EXECUTABLE={python_exe}",
            f"-DPython3_ROOT_DIR={python_root}",
            "-DPython3_FIND_STRATEGY=LOCATION",
            "-DPython3_FIND_REGISTRY=NEVER",
        ]

        # Explicitly pass the lib path if we found it, so the MSVC linker
        # doesn't fall back to the x64 hostedtoolcache python*.lib
        if python_lib.exists():
            cmake_args.append(f"-DPython3_LIBRARY={python_lib}")

        # Honour VCPKG on Windows
        vcpkg_root = os.environ.get("VCPKG_ROOT")
        if vcpkg_root:
            cmake_args.append(
                f"-DCMAKE_TOOLCHAIN_FILE={vcpkg_root}/scripts/buildsystems/vcpkg.cmake"
            )

        build_dir = Path(self.build_temp) / ext.name
        build_dir.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["cmake", str(ext.source_dir), *cmake_args],
            cwd=build_dir, check=True,
        )
        subprocess.run(
            ["cmake", "--build", ".", "--config", build_type, "--parallel"],
            cwd=build_dir, check=True,
        )


setup(
    name="loom-python-plugin",
    version="0.1.0",
    ext_modules=[CMakeExtension("loom", source_dir="src/loom")],
    cmdclass={"build_ext": CMakeBuild},
    zip_safe=False,
)
