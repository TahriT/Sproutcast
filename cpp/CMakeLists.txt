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

add_executable(plantvision_cpp 
    src/main.cpp 
    src/mqtt_client.cpp 
    src/leaf_area.cpp
)

target_include_directories(plantvision_cpp PRIVATE 
    ${OpenCV_INCLUDE_DIRS} 
    include
    ${NLOHMANN_JSON_INCLUDE_DIR}
)

target_link_libraries(plantvision_cpp PRIVATE ${OpenCV_LIBS})

if(nlohmann_json_FOUND)
    target_link_libraries(plantvision_cpp PRIVATE nlohmann_json::nlohmann_json)
endif()

