# Minimum CMake version
cmake_minimum_required(VERSION 3.10)

# Project name
project(loom_qgis_plugin LANGUAGES CXX)

# Set the C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Use modern FindPython with pybind11
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 REQUIRED)

# Include directories for the project
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src/loom/src)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src/loom/src/loom)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src/loom/src/util)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src/loom/src/shared)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src/loom/src/octi)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src/loom/src/topo)
include_directories(${CMAKE_CURRENT_BINARY_DIR})  # Add the build directory

# Configure _config.h
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/_config.h.in"
    "${CMAKE_CURRENT_BINARY_DIR}/loom/_config.h"
)

# Set the output directory for shared libraries
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/lib)

# ============================
# Python Shared Library 1 (loom_python)
# ============================

# Add source files for the first Python module
set(LOOM_PYTHON_SOURCES
    src/loom/src/loom/Bindings.cpp
    src/loom/src/loom/LoomMain.cpp
)

# Create the first Python module
pybind11_add_module(loom_python ${LOOM_PYTHON_SOURCES})

# Link the required libraries to loom_python
target_link_libraries(loom_python PRIVATE loom_dep shared_dep dot_dep pb_util_graph pb_util pb_util_json pb_util_geo -lpthread)

# Set output properties for the first Python module
set_target_properties(loom_python PROPERTIES
    PREFIX ""  # Remove the "lib" prefix
    SUFFIX ".so"  # Ensure the output is a Python module
)

# ============================
# Python Shared Library 2 (octi_python)
# ============================

# Add source files for the second Python module
set(OCTI_PYTHON_SOURCES
    src/loom/src/octi/Bindings.cpp
    src/loom/src/octi/OctiMain.cpp
)

# Create the second Python module
pybind11_add_module(octi_python ${OCTI_PYTHON_SOURCES})

# Link the required libraries to octi_python
target_link_libraries(octi_python PRIVATE octi_dep shared_dep pb_util_geo pb_util_graph pb_util_json pb_util dot_dep -lpthread)

# Set output properties for the second Python module
set_target_properties(octi_python PROPERTIES
    PREFIX ""  # Remove the "lib" prefix
    SUFFIX ".so"  # Ensure the output is a Python module
)

# ============================
# Python Shared Library 3 (topo_python)
# ============================

# Add source files for the third Python module
set(TOPO_PYTHON_SOURCES
    src/loom/src/topo/Bindings.cpp
    src/loom/src/topo/TopoMain.cpp
)

# Create the third Python module
pybind11_add_module(topo_python ${TOPO_PYTHON_SOURCES})

# Link the required libraries to topo_python
target_link_libraries(topo_python PRIVATE topo_dep shared_dep dot_dep pb_util_geo pb_util_graph pb_util_json pb_util -lpthread)

# Set output properties for the third Python module
set_target_properties(topo_python PROPERTIES
    PREFIX ""  # Remove the "lib" prefix
    SUFFIX ".so"  # Ensure the output is a Python module
)


