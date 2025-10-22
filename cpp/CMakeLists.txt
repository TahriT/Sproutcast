cmake_minimum_required(VERSION 3.16)
project(plantvision_cpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCV REQUIRED)
find_package(nlohmann_json QUIET)
if(NOT nlohmann_json_FOUND)
    # Fallback for systems without nlohmann_json package
    find_path(NLOHMANN_JSON_INCLUDE_DIR nlohmann/json.hpp
        HINTS /usr/include /usr/local/include)
    if(NLOHMANN_JSON_INCLUDE_DIR)
        message(STATUS "Found nlohmann/json headers at ${NLOHMANN_JSON_INCLUDE_DIR}")
    else()
        message(WARNING "nlohmann/json not found - may cause compilation issues")
    endif()
endif()

# Find ONNX Runtime (optional for AI inference)
find_path(ONNXRUNTIME_INCLUDE_DIR onnxruntime_cxx_api.h
    HINTS /usr/include/onnxruntime /usr/local/include/onnxruntime)
find_library(ONNXRUNTIME_LIB onnxruntime
    HINTS /usr/lib /usr/local/lib)

if(ONNXRUNTIME_INCLUDE_DIR AND ONNXRUNTIME_LIB)
    message(STATUS "Found ONNX Runtime: ${ONNXRUNTIME_LIB}")
    set(HAVE_ONNXRUNTIME ON)
else()
    message(STATUS "ONNX Runtime not found - AI models will use Python fallback")
    set(HAVE_ONNXRUNTIME OFF)
endif()

add_executable(plantvision_cpp 
    src/main.cpp 
    src/mqtt_client.cpp 
    src/leaf_area.cpp
    src/vision_processor.cpp
    src/morphology_analysis.cpp
)

target_include_directories(plantvision_cpp PRIVATE 
    ${OpenCV_INCLUDE_DIRS} 
    include
    ${NLOHMANN_JSON_INCLUDE_DIR}
)

# Only add ONNX Runtime include dir if found
if(HAVE_ONNXRUNTIME)
    target_include_directories(plantvision_cpp PRIVATE ${ONNXRUNTIME_INCLUDE_DIR})
endif()

# Add filesystem library support for C++17 std::filesystem
target_link_libraries(plantvision_cpp PRIVATE ${OpenCV_LIBS})

if(nlohmann_json_FOUND)
    target_link_libraries(plantvision_cpp PRIVATE nlohmann_json::nlohmann_json)
endif()

if(HAVE_ONNXRUNTIME)
    target_link_libraries(plantvision_cpp PRIVATE ${ONNXRUNTIME_LIB})
    target_compile_definitions(plantvision_cpp PRIVATE HAVE_ONNXRUNTIME)
endif()

