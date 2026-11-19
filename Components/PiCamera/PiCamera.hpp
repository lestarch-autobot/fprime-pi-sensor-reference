// ======================================================================
// \title  PiCamera.hpp
// \brief  hpp file for PiCamera component implementation class
// ======================================================================

#ifndef PiSensor_PiCamera_HPP
#define PiSensor_PiCamera_HPP

#include "Components/PiCamera/Camera.hpp"
#include "Components/PiCamera/FppConstantsAc.hpp"
#include "Components/PiCamera/PiCameraComponentAc.hpp"

namespace PiSensor {

class PiCamera final : public PiCameraComponentBase {
    friend class PiCameraTester;

  public:
    //! Construct PiCamera object
    explicit PiCamera(const char* const compName  //!< The component name
             );

    //! Destroy PiCamera object
    ~PiCamera();

    PiCamera(const PiCamera&) = delete;
    PiCamera& operator=(const PiCamera&) = delete;

    //! Set the camera and the telemetry channels read at each capture.
    //! Called once before the component thread starts.
    void configure(Camera& camera,                 //!< The camera interface
                   FwChanIdType temperatureChannel,  //!< Channel of type Bmp280.Bmp280Data
                   FwChanIdType attitudeChannel,     //!< Channel of type MpuImu.ImuData
                   FwChanIdType locationChannel      //!< Channel of type NmeaGps.GpsData
                   );

  private:
    //! Result of one step of a capture
    struct StepResult {
        bool ok;
        PiCamera_FailReason reason;
        PiCamera_FailStep step;
        I32 code;
    };

    //! Publish the channels when the component thread starts
    void preamble() override;

    //! Handler implementation for pingIn
    void pingIn_handler(FwIndexType portNum,  //!< The port number
                        U32 key               //!< Value to return to pinger
                        ) override;

    //! Handler implementation for command CAPTURE
    void CAPTURE_cmdHandler(FwOpcodeType opCode,  //!< The opcode
                            U32 cmdSeq            //!< The command sequence number
                            ) override;

    //! Handler implementation for acquire
    void acquire_internalInterfaceHandler(FwOpcodeType opCode,  //!< Opcode of the command the capture answers
                                          U32 cmdSeq            //!< Sequence number of that command
                                          ) override;

    //! Steps DETECT to FRAME
    StepResult acquireFrame();

    //! Steps TEMPERATURE, ATTITUDE, LOCATION
    StepResult readMetrics(const Fw::Time& captureTime, PiCamera_CaptureMetrics& metrics);

    //! Read one channel and check that a value is present
    StepResult readChannel(FwChanIdType channel, PiCamera_FailStep step, Fw::Time& sampleTime, Fw::TlmBuffer& value);

    //! Check that a sample time is within METRIC_MAX_AGE_MS of the capture time
    static StepResult checkAge(PiCamera_FailStep step, const Fw::Time& captureTime, const Fw::Time& sampleTime);

    //! Step ENCODE
    StepResult encode(FwSizeType& size);

    //! Step CONTAINER and the sending of the container
    StepResult store(const Fw::Time& captureTime, const PiCamera_CaptureMetrics& metrics, FwSizeType size);

    //! Count the result, publish the changed channels and clear the busy flag
    void endCapture(bool success, U32 size);

    //! Map a camera status to a step result
    static StepResult cameraResult(Camera::Status status, PiCamera_FailStep step, I32 code);

    //! A failed step
    static StepResult failure(PiCamera_FailReason reason, PiCamera_FailStep step, I32 code);

    //! A step that succeeded
    static StepResult success();

    //! Roll in degrees from an acceleration
    static F32 roll(F32 ax, F32 ay, F32 az);

    //! Pitch in degrees from an acceleration
    static F32 pitch(F32 ax, F32 ay, F32 az);

    Camera* m_camera;                      //!< The camera interface
    FwChanIdType m_temperatureChannel;     //!< Channel of the temperature reading
    FwChanIdType m_attitudeChannel;        //!< Channel of the acceleration reading
    FwChanIdType m_locationChannel;        //!< Channel of the location reading
    bool m_busy;                           //!< A capture is accepted and has not ended
    U32 m_completed;                       //!< Captures that stored a product
    U32 m_failed;                          //!< CAPTURE commands that failed
    U8 m_jpeg[PiCamera_PICTURE_MAX_SIZE];  //!< Encoded picture
};

}  // namespace PiSensor

#endif
