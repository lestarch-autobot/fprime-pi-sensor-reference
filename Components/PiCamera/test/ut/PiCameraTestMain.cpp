// ======================================================================
// \title  PiCameraTestMain.cpp
// \brief  cpp file for PiCamera component test main function
// ======================================================================

#include "Components/PiCamera/CameraFactory.hpp"
#include "Fw/Test/UnitTest.hpp"
#include "PiCameraTester.hpp"
#include "STest/Random/Random.hpp"

#define PICAMERA_TEST(NAME, REQUIREMENTS, DESCRIPTION) \
    TEST(PiCamera, NAME) {                             \
        COMMENT(DESCRIPTION);                          \
        REQUIREMENT(REQUIREMENTS);                     \
        PiSensor::PiCameraTester tester;               \
        tester.test##NAME();                           \
    }

PICAMERA_TEST(NominalCapture, "REQ-PiCamera-004, REQ-PiCamera-014", "One container with one Metrics and one Picture record, one OK")
PICAMERA_TEST(MetricsCopied, "REQ-PiCamera-005", "Latitude, longitude and temperature equal the readings in the store")
PICAMERA_TEST(RollPitch, "REQ-PiCamera-006", "Roll and pitch equal the formula within 0.01 degrees")
PICAMERA_TEST(CaptureTime, "REQ-PiCamera-007", "Capture time and container time tag are the time at the frame")
PICAMERA_TEST(SampleTimes, "REQ-PiCamera-008", "The three sample times equal the time tags in the store")
PICAMERA_TEST(FrameTimeout, "REQ-PiCamera-023, REQ-PiCamera-015", "No frame fails with TIMEOUT at FRAME")
PICAMERA_TEST(StaleReading, "REQ-PiCamera-010, REQ-PiCamera-013, REQ-PiCamera-026", "A reading older or newer than the limit fails with SENSOR_STALE")
PICAMERA_TEST(MissingReading, "REQ-PiCamera-011, REQ-PiCamera-013, REQ-PiCamera-026", "A reading that is absent or does not decode fails with SENSOR_NO_DATA")
PICAMERA_TEST(AttitudeUnavailable, "REQ-PiCamera-026, REQ-PiCamera-006, REQ-PiCamera-010, REQ-PiCamera-011", "A missing or stale acceleration stores the product with NaN, the flag false and a warning")
PICAMERA_TEST(InvalidMetric, "REQ-PiCamera-012, REQ-PiCamera-013", "A value that is not finite or out of range fails with METRIC_INVALID")
PICAMERA_TEST(NoCamera, "REQ-PiCamera-016, REQ-PiCamera-015", "No camera listed fails with NO_CAMERA at DETECT")
PICAMERA_TEST(CameraErrors, "REQ-PiCamera-016, REQ-PiCamera-015", "A failure at each camera step fails with CAMERA_ERROR and closes the camera")
PICAMERA_TEST(TooLarge, "REQ-PiCamera-017", "A JPEG of PICTURE_MAX_SIZE passes, one byte more fails with TOO_LARGE")
PICAMERA_TEST(NoContainer, "REQ-PiCamera-017, REQ-PiCamera-013", "A failed container request fails with NO_CONTAINER")
PICAMERA_TEST(FailureResponse, "REQ-PiCamera-013, REQ-PiCamera-014, REQ-PiCamera-015", "Every failure gives one EXECUTION_ERROR, one CaptureFailed and no container")
PICAMERA_TEST(BusyDuringCapture, "REQ-PiCamera-018, REQ-PiCamera-014", "A command during a capture gets BUSY and does not change the capture")
PICAMERA_TEST(RecoveryAfterFailure, "REQ-PiCamera-019", "After each failure reason the next capture succeeds")
PICAMERA_TEST(Events, "REQ-PiCamera-020, REQ-PiCamera-025", "CaptureStarted before the first camera call, CaptureCompleted with the size")
PICAMERA_TEST(TelemetryOnChange, "REQ-PiCamera-021", "Channels published at thread start and when they change")
PICAMERA_TEST(Ping, "REQ-PiCamera-022", "A ping is echoed with its key")
PICAMERA_TEST(RandomSequences, "REQ-PiCamera-014, REQ-PiCamera-018, REQ-PiCamera-021", "Random sequences keep one response per command and the counts equal to the responses")

#ifdef PICAMERA_NO_CAMERA_BUILD
TEST(PiCamera, NoCameraBuild) {
    COMMENT("The camera of a PICAMERA_NO_CAMERA build reports no camera at every call");
    REQUIREMENT("REQ-PiCamera-016");
    PiSensor::Camera& camera = PiSensor::getCamera();
    I32 code = 1;
    U8 data[4] = {};
    FwSizeType size = sizeof(data);
    ASSERT_EQ(camera.detect(code), PiSensor::Camera::Status::NO_CAMERA);
    ASSERT_EQ(code, 0);
    ASSERT_EQ(camera.open(code), PiSensor::Camera::Status::NO_CAMERA);
    ASSERT_EQ(camera.configure(640, 480, code), PiSensor::Camera::Status::NO_CAMERA);
    ASSERT_EQ(camera.start(code), PiSensor::Camera::Status::NO_CAMERA);
    ASSERT_EQ(camera.waitFrame(1, 0, code), PiSensor::Camera::Status::NO_CAMERA);
    ASSERT_EQ(camera.encode(90, data, sizeof(data), size, code), PiSensor::Camera::Status::NO_CAMERA);
    ASSERT_EQ(size, 0U);
    camera.stop();
    camera.close();
    ASSERT_EQ(&camera, &PiSensor::getCamera());
}
#endif

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    STest::Random::seed();
    return RUN_ALL_TESTS();
}
