// ======================================================================
// \title  CameraFactory.hpp
// \brief  Access to the camera interface the build selected
// ======================================================================

#ifndef PiSensor_CameraFactory_HPP
#define PiSensor_CameraFactory_HPP

#include "Components/PiCamera/Camera.hpp"

namespace PiSensor {

//! The camera of this build: libcamera and libjpeg, or, with the CMake
//! option PICAMERA_NO_CAMERA, an interface that detects no camera.
//! The object is created on the first call; call it during initialization.
Camera& getCamera();

}  // namespace PiSensor

#endif
