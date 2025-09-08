cmake_minimum_required(VERSION 3.16)
project(plantvision_cpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCV REQUIRED)

add_executable(plantvision_cpp src/main.cpp src/mqtt_client.cpp src/leaf_area.cpp)

target_include_directories(plantvision_cpp PRIVATE ${OpenCV_INCLUDE_DIRS} include)

target_link_libraries(plantvision_cpp PRIVATE ${OpenCV_LIBS})

