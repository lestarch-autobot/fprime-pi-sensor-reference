// ======================================================================
// \title  PiCameraTester.hpp
// \brief  hpp file for PiCamera component test harness implementation class
// ======================================================================

#ifndef PiSensor_PiCameraTester_HPP
#define PiSensor_PiCameraTester_HPP

#include "Components/PiCamera/PiCamera.hpp"
#include "Components/PiCamera/PiCameraGTestBase.hpp"
#include "Components/PiCamera/test/ut/FakeCamera.hpp"
#include "STest/Scenario/BoundedScenario.hpp"
#include "STest/Scenario/RandomScenario.hpp"
#include "TestUtils/RuleBasedTesting.hpp"

namespace PiSensor {

class PiCameraTester final : public PiCameraGTestBase {
  public:
    static const FwSizeType MAX_HISTORY_SIZE = 100;
    static const FwEnumStoreType TEST_INSTANCE_ID = 0;
    static const FwSizeType TEST_INSTANCE_QUEUE_DEPTH = 5;

    //! Channels given to configure
    enum Channel { TEMPERATURE = 0, ATTITUDE = 1, LOCATION = 2, NUM_CHANNELS = 3 };
    static constexpr FwChanIdType CHANNEL_ID[NUM_CHANNELS] = {0x1100, 0x2200, 0x3300};

    //! One entry of the substitute telemetry store
    struct StoreEntry {
        Fw::TlmValid valid;
        Fw::Time time;
        Fw::TlmBuffer value;
    };

    //! What a container held
    struct Product {
        Fw::Time timeTag;
        FwDpPriorityType priority;
        PiCamera_CaptureMetrics metrics;
        FwSizeType pictureSize;
        bool pictureMatches;  //!< Every picture byte equals the substitute's fill
        U32 records;
        U32 metricsRecords;
        U32 pictureRecords;
    };

    PiCameraTester();
    ~PiCameraTester();

    // Tests of SDD section 8
    void testNominalCapture();
    void testMetricsCopied();
    void testRollPitch();
    void testCaptureTime();
    void testSampleTimes();
    void testFrameTimeout();
    void testStaleReading();
    void testMissingReading();
    void testAttitudeUnavailable();
    void testInvalidMetric();
    void testNoCamera();
    void testCameraErrors();
    void testTooLarge();
    void testNoContainer();
    void testFailureResponse();
    void testBusyDuringCapture();
    void testRecoveryAfterFailure();
    void testEvents();
    void testTelemetryOnChange();
    void testPing();
    void testRandomSequences();

    // Rules for random sequences
    FW_RBT_DEFINE_RULE(PiCameraTester, Capture, Nominal);
    FW_RBT_DEFINE_RULE(PiCameraTester, Capture, Busy);
    FW_RBT_DEFINE_RULE(PiCameraTester, Capture, CameraFailure);
    FW_RBT_DEFINE_RULE(PiCameraTester, Capture, SensorFailure);
    FW_RBT_DEFINE_RULE(PiCameraTester, Capture, NoBuffer);
    FW_RBT_DEFINE_RULE(PiCameraTester, Health, Ping);

  private:
    // Generated helpers
    void connectPorts();
    void initComponents();

    // Substitutes
    Fw::TlmValid from_tlmGetOut_handler(FwIndexType portNum,
                                        FwChanIdType id,
                                        Fw::Time& timeTag,
                                        Fw::TlmBuffer& val) override;
    Fw::Success::T productGet_handler(FwDpIdType id, FwSizeType dataSize, Fw::Buffer& buffer) override;
    void cmdResponseIn(FwOpcodeType opCode, U32 cmdSeq, Fw::CmdResponse response) override;

    // Helpers: set-up
    //! Camera, store and buffers as a capture that succeeds needs them
    void setNominal();
    void setTemperature(F32 temperature, const Fw::Time& time);
    void setAcceleration(F32 x, F32 y, F32 z, const Fw::Time& time);
    void setLocation(F64 latitude, F64 longitude, const Fw::Time& time);
    //! A time offsetUsec after the capture time
    Fw::Time timeAt(I64 offsetUsec) const;

    // Helpers: stimulus
    //! Send CAPTURE and run the component thread until its queue is empty
    void capture();
    void dispatchAll();
    void ping(U32 key);

    // Helpers: checks
    //! attitudeValid false: the product has NaN for roll and pitch and AttitudeUnavailable was emitted
    void assertSuccess(FwSizeType pictureSize, bool attitudeValid = true);
    void assertFailure(PiCamera_FailReason reason, PiCamera_FailStep step, I32 code);
    //! capture() and assertFailure(), then a capture with the nominal set-up that succeeds
    void captureFails(PiCamera_FailReason reason, PiCamera_FailStep step, I32 code);
    //! A capture that succeeds without roll and pitch, then one with the nominal set-up that has them
    void captureWithoutAttitude(PiCamera_FailReason reason, I32 code);
    //! captureFails() for the temperature and the location, captureWithoutAttitude() for the acceleration
    void captureLacks(U32 channel, PiCamera_FailReason reason, I32 code);
    void assertCameraClosed();
    Product readProduct(U32 index);

    // Shadow state of the random sequences
    U32 m_expectedCompleted;
    U32 m_expectedFailed;
    U32 m_commands;
    U32 m_responses;

    U32 m_cmdSeq;                       //!< Sequence number of the last command
    Fw::Time m_captureTime;             //!< Time set when the frame is handed over
    StoreEntry m_store[NUM_CHANNELS];   //!< The substitute telemetry store
    std::function<void()> m_onResponse;  //!< Runs inside a command response
    bool m_bufferAvailable;             //!< productGet hands out a buffer
    FakeCamera m_camera;
    PiCamera component;

    static U8 s_productBuffer[PiCamera_PICTURE_MAX_SIZE + 4096];
};

}  // namespace PiSensor

#endif
