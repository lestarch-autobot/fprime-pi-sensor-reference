####
# PiSensor::PiCamera
#
# The camera interface is built on libcamera and libjpeg (Raspberry Pi OS
# packages libcamera-dev and libjpeg62-turbo-dev). PICAMERA_SYSROOT names a
# directory that holds the unpacked packages when they are not installed.
# PICAMERA_NO_CAMERA=ON builds an interface that detects no camera instead
# (hosts without libcamera). With the option off, a build that does not find
# the libraries fails.
####
option(PICAMERA_NO_CAMERA "Build PiCamera with a camera interface that detects no camera" OFF)
set(PICAMERA_SYSROOT "" CACHE PATH "Directory holding unpacked libcamera-dev and libjpeg62-turbo-dev packages")

if (PICAMERA_NO_CAMERA)
    set(PICAMERA_CAMERA_SOURCE "${CMAKE_CURRENT_LIST_DIR}/NoCamera.cpp")
else()
    set(PICAMERA_CAMERA_SOURCE "${CMAKE_CURRENT_LIST_DIR}/LibcameraCamera.cpp")
    file(GLOB PICAMERA_ARCH_DIRS "${PICAMERA_SYSROOT}/usr/include/*-linux-gnu" "${PICAMERA_SYSROOT}/usr/lib/*-linux-gnu")
    find_path(PICAMERA_LIBCAMERA_INCLUDE libcamera/libcamera.h
        HINTS "${PICAMERA_SYSROOT}/usr/include/libcamera" PATH_SUFFIXES libcamera)
    find_path(PICAMERA_JPEG_INCLUDE jpeglib.h HINTS "${PICAMERA_SYSROOT}/usr/include")
    find_path(PICAMERA_JCONFIG_INCLUDE jconfig.h HINTS ${PICAMERA_ARCH_DIRS} "${PICAMERA_SYSROOT}/usr/include")
    find_library(PICAMERA_LIBCAMERA_LIBRARY camera HINTS ${PICAMERA_ARCH_DIRS})
    find_library(PICAMERA_LIBCAMERA_BASE_LIBRARY camera-base HINTS ${PICAMERA_ARCH_DIRS})
    find_library(PICAMERA_JPEG_LIBRARY jpeg HINTS ${PICAMERA_ARCH_DIRS})
    foreach (PICAMERA_FOUND IN ITEMS PICAMERA_LIBCAMERA_INCLUDE PICAMERA_JPEG_INCLUDE PICAMERA_JCONFIG_INCLUDE
             PICAMERA_LIBCAMERA_LIBRARY PICAMERA_LIBCAMERA_BASE_LIBRARY PICAMERA_JPEG_LIBRARY)
        if (NOT ${PICAMERA_FOUND})
            message(FATAL_ERROR "PiCamera: ${PICAMERA_FOUND} not found. Install libcamera-dev and libjpeg62-turbo-dev, "
                                "set PICAMERA_SYSROOT, or set PICAMERA_NO_CAMERA=ON")
        endif()
    endforeach()
endif()

register_fprime_library(
    AUTOCODER_INPUTS
        "${CMAKE_CURRENT_LIST_DIR}/PiCamera.fpp"
    SOURCES
        "${CMAKE_CURRENT_LIST_DIR}/PiCamera.cpp"
        "${PICAMERA_CAMERA_SOURCE}"
    DEPENDS
        fprime-sensors_Bmp280_Types
        fprime-sensors_MpuImu_Types
        fprime-sensors_NmeaGps_Types
)

if (NOT PICAMERA_NO_CAMERA)
    # libcamera needs C++17; its headers are not held to the project's warnings
    set_source_files_properties("${PICAMERA_CAMERA_SOURCE}" PROPERTIES COMPILE_OPTIONS "-std=c++17")
    target_include_directories(Components_PiCamera SYSTEM PRIVATE
        "${PICAMERA_LIBCAMERA_INCLUDE}" "${PICAMERA_JPEG_INCLUDE}" "${PICAMERA_JCONFIG_INCLUDE}")
    target_link_libraries(Components_PiCamera PUBLIC
        "${PICAMERA_LIBCAMERA_LIBRARY}" "${PICAMERA_LIBCAMERA_BASE_LIBRARY}" "${PICAMERA_JPEG_LIBRARY}")
endif()
