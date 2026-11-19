// ======================================================================
// \title  Camera.hpp
// \brief  Interface between PiCamera and the camera and JPEG libraries
// ======================================================================

#ifndef PiSensor_Camera_HPP
#define PiSensor_Camera_HPP

#include "Fw/FPrimeBasicTypes.hpp"

namespace PiSensor {

//! One camera, used for one capture at a time: detect, open, configure,
//! start, waitFrame, encode, stop, close. The frame handed over by
//! waitFrame stays inside the object until stop.
class Camera {
  public:
    enum class Status : U8 {
        OK,         //!< The call succeeded
        NO_CAMERA,  //!< The camera library lists no camera
        ERROR,      //!< A library call failed or the frame is in error or incomplete
        TIMEOUT,    //!< No frame arrived within the limit
        TOO_LARGE,  //!< The JPEG does not fit the destination
    };

    virtual ~Camera() = default;

    //! List the cameras
    virtual Status detect(I32& code  //!< Return code of the failing library call, else 0
                          ) = 0;

    //! Open the first camera
    virtual Status open(I32& code) = 0;

    //! Ask for frames of width x height pixels, YUV420
    virtual Status configure(U32 width, U32 height, I32& code) = 0;

    //! Start the stream
    virtual Status start(I32& code) = 0;

    //! Discard settleFrames frames and keep the next one. The wait is
    //! limited to timeoutMs on a monotonic clock.
    virtual Status waitFrame(U32 timeoutMs, U32 settleFrames, I32& code) = 0;

    //! Encode the kept frame as a JPEG into dst
    virtual Status encode(U32 quality,          //!< libjpeg quality, 1 to 100
                          U8* dst,              //!< Destination
                          FwSizeType capacity,  //!< Size of the destination in bytes
                          FwSizeType& size,     //!< Size of the JPEG in bytes
                          I32& code) = 0;

    //! Stop the stream. Returns only after no frame callback can run.
    virtual void stop() = 0;

    //! Release the camera. Safe to call in any state.
    virtual void close() = 0;
};

}  // namespace PiSensor

#endif
