cmake_minimum_required(VERSION 3.24.2)
project(PiSensorReference C CXX)

include("${CMAKE_CURRENT_LIST_DIR}/lib/fprime/cmake/FPrime.cmake")
fprime_setup_included_code()

add_fprime_subdirectory("${CMAKE_CURRENT_LIST_DIR}/SystemTester")
add_fprime_subdirectory("${CMAKE_CURRENT_LIST_DIR}/PiSensor")
