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

        cmake_args = [
            f"-Dpybind11_DIR={pybind11.get_cmake_dir()}",
            f"-DCMAKE_BUILD_TYPE={build_type}",
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={ext_dir}",
            f"-DPYTHON_EXECUTABLE={sys.executable}",
            # Tell cmake to use exactly the Python running this script
            f"-DPython3_EXECUTABLE={sys.executable}",
            f"-DPython3_ROOT_DIR={Path(sys.executable).parent.parent}",
            "-DPython3_FIND_STRATEGY=LOCATION",
            # Only need headers for extension modules, not libpython
            "-DPYTHON_FIND_IMPLEMENTATIONS=CPython",
        ]

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
