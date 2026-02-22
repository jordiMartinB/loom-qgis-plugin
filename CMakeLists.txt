# Minimum CMake version
cmake_minimum_required(VERSION 3.12)  # Use at least CMake 3.12 for FindPython3

# Set CMake policy CMP0079 to NEW
cmake_policy(SET CMP0079 NEW)

# Set CMake policy CMP0148 to NEW
cmake_policy(SET CMP0148 NEW)

# Project name
project(loom_qgis_plugin LANGUAGES CXX)

# Set the C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Option to build tests
option(BUILD_TESTS "Build tests" OFF)

# Use modern FindPython with pybind11
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 REQUIRED)

# Use modern Python3 module
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

# Include Python3 headers
include_directories(${Python3_INCLUDE_DIRS})

# Configure _config.h
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/_config.h.in"
    "${CMAKE_CURRENT_BINARY_DIR}/loom/_config.h"
)

# Set the output directory for shared libraries
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/lib)
set(CMAKE_BUILD_TYPE Debug)

# Force position independent code so static archives can be linked into shared libs
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# ============================
# Add Subdirectories for Libraries
# ============================

# Add the util directory early so its targets / include settings are available
add_subdirectory(src/loom/src/util)

# Add other required subdirectories
add_subdirectory(src/loom/src/shared)  # shared_dep
add_subdirectory(src/loom/src/octi)    # octi_dep
add_subdirectory(src/loom/src/dot)     # dot_dep
add_subdirectory(src/loom/src/loom)     # loom_dep
add_subdirectory(src/loom/src/topo)     # topo_dep

# Ensure include root points to src/loom/src (so includes like "util/Misc.h" work)
target_include_directories(dot_dep PUBLIC ${PROJECT_SOURCE_DIR}/src/loom/src)
target_include_directories(shared_dep PUBLIC ${PROJECT_SOURCE_DIR}/src/loom/src)
target_include_directories(pb_util_json PUBLIC ${PROJECT_SOURCE_DIR}/src/loom/src)
target_include_directories(pb_util_xml PUBLIC ${PROJECT_SOURCE_DIR}/src/loom/src)
target_include_directories(pb_util_http PUBLIC ${PROJECT_SOURCE_DIR}/src/loom/src)

# ============================
# Python Shared Libraries
# ============================

# Add Python shared libraries (loom_python, octi_python, topo_python)

# ============================
# Python Shared Library 1 (loom_python)
# ============================

# Add source files for the first Python module
set(LOOM_PYTHON_SOURCES
    src/loom/src/loom/Bindings.cpp
    src/loom/src/loom/Loom.cpp
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
    src/loom/src/octi/Octi.cpp
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
    src/loom/src/topo/Topo.cpp
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

# Provide an include-only target so targets can link "loom_includes" without producing -lloom_includes
if(NOT TARGET loom_includes)
    add_library(loom_includes INTERFACE)
    target_include_directories(loom_includes INTERFACE
        ${PROJECT_SOURCE_DIR}/src/loom/src     # headers like "util/..." live here
        ${CMAKE_CURRENT_BINARY_DIR}/loom       # generated loom/_config.h
    )
endif()



