####
# PiSensor::PiCamera
#
# PICAMERA_NO_CAMERA=ON builds the camera interface that detects no camera
# (hosts without libcamera). With the option off, libcamera and libjpeg
# must be found or the build fails.
####
option(PICAMERA_NO_CAMERA "Build PiCamera with a camera interface that detects no camera" OFF)

register_fprime_library(
    AUTOCODER_INPUTS
        "${CMAKE_CURRENT_LIST_DIR}/PiCamera.fpp"
    SOURCES
        "${CMAKE_CURRENT_LIST_DIR}/PiCamera.cpp"
    DEPENDS
        fprime-sensors_Bmp280_Types
        fprime-sensors_MpuImu_Types
        fprime-sensors_NmeaGps_Types
)
