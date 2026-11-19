// ======================================================================
// \title  PiCameraTester.cpp
// \brief  cpp file for PiCamera component test harness implementation class
// ======================================================================

#include "PiCameraTester.hpp"

#include <cmath>
#include <limits>

#include "Fw/Dp/DpContainer.hpp"
#include "STest/Pick/Pick.hpp"
#include "fprime-sensors/Bmp280/Types/Bmp280DataSerializableAc.hpp"
#include "fprime-sensors/MpuImu/Types/ImuDataSerializableAc.hpp"
#include "fprime-sensors/NmeaGps/Types/GpsDataSerializableAc.hpp"

namespace PiSensor {

constexpr FwChanIdType PiCameraTester::CHANNEL_ID[NUM_CHANNELS];
U8 PiCameraTester::s_productBuffer[PiCamera_PICTURE_MAX_SIZE + 4096];

namespace {
constexpr I64 USEC_PER_SEC = 1000000;
constexpr I64 MAX_AGE_USEC = static_cast<I64>(PiCamera_METRIC_MAX_AGE_MS) * 1000;
constexpr U32 CAPTURE_SECONDS = 1000000;
constexpr F64 PI = 3.14159265358979323846;
}  // namespace

// ----------------------------------------------------------------------
// Construction and destruction
// ----------------------------------------------------------------------

PiCameraTester::PiCameraTester()
    : PiCameraGTestBase("PiCameraTester", PiCameraTester::MAX_HISTORY_SIZE),
      m_expectedCompleted(0),
      m_expectedFailed(0),
      m_commands(0),
      m_responses(0),
      m_cmdSeq(0),
      m_captureTime(TimeBase::TB_WORKSTATION_TIME, CAPTURE_SECONDS, 500000),
      m_bufferAvailable(true),
      component("PiCamera") {
    this->initComponents();
    this->connectPorts();
    this->component.configure(this->m_camera, CHANNEL_ID[TEMPERATURE], CHANNEL_ID[ATTITUDE], CHANNEL_ID[LOCATION]);
    this->setNominal();
}

PiCameraTester::~PiCameraTester() {
    this->component.deinit();
}

// ----------------------------------------------------------------------
// Substitutes
// ----------------------------------------------------------------------

Fw::TlmValid PiCameraTester::from_tlmGetOut_handler(FwIndexType portNum,
                                                    FwChanIdType id,
                                                    Fw::Time& timeTag,
                                                    Fw::TlmBuffer& val) {
    for (U32 i = 0; i < NUM_CHANNELS; i++) {
        if (id == CHANNEL_ID[i]) {
            timeTag = this->m_store[i].time;
            val = this->m_store[i].value;
            return this->m_store[i].valid;
        }
    }
    val.resetSer();
    return Fw::TlmValid::INVALID;
}

Fw::Success::T PiCameraTester::productGet_handler(FwDpIdType id, FwSizeType dataSize, Fw::Buffer& buffer) {
    this->pushProductGetEntry(id, dataSize);
    // dataSize is the size of the whole packet
    const FwSizeType size = dataSize;
    if ((!this->m_bufferAvailable) || (size > sizeof(s_productBuffer))) {
        return Fw::Success::FAILURE;
    }
    buffer.set(s_productBuffer, size, 0);
    return Fw::Success::SUCCESS;
}

void PiCameraTester::cmdResponseIn(FwOpcodeType opCode, U32 cmdSeq, Fw::CmdResponse response) {
    PiCameraGTestBase::cmdResponseIn(opCode, cmdSeq, response);
    if (this->m_onResponse) {
        this->m_onResponse();
    }
}

// ----------------------------------------------------------------------
// Helpers: set-up
// ----------------------------------------------------------------------

Fw::Time PiCameraTester::timeAt(I64 offsetUsec) const {
    const I64 total = static_cast<I64>(this->m_captureTime.getSeconds()) * USEC_PER_SEC +
                      static_cast<I64>(this->m_captureTime.getUSeconds()) + offsetUsec;
    return Fw::Time(this->m_captureTime.getTimeBase(), static_cast<U32>(total / USEC_PER_SEC),
                    static_cast<U32>(total % USEC_PER_SEC));
}

void PiCameraTester::setTemperature(F32 temperature, const Fw::Time& time) {
    Bmp280::Bmp280Data data(101325.0F, temperature, 10.0F);
    this->m_store[TEMPERATURE].valid = Fw::TlmValid::VALID;
    this->m_store[TEMPERATURE].time = time;
    this->m_store[TEMPERATURE].value.resetSer();
    ASSERT_EQ(this->m_store[TEMPERATURE].value.serializeFrom(data), Fw::FW_SERIALIZE_OK);
}

void PiCameraTester::setAcceleration(F32 x, F32 y, F32 z, const Fw::Time& time) {
    MpuImu::ImuData data;
    FprimeSensors::GeometricVector3 acceleration(x, y, z);
    data.set_acceleration(acceleration);
    this->m_store[ATTITUDE].valid = Fw::TlmValid::VALID;
    this->m_store[ATTITUDE].time = time;
    this->m_store[ATTITUDE].value.resetSer();
    ASSERT_EQ(this->m_store[ATTITUDE].value.serializeFrom(data), Fw::FW_SERIALIZE_OK);
}

void PiCameraTester::setLocation(F64 latitude, F64 longitude, const Fw::Time& time) {
    NmeaGps::GpsData data(latitude, longitude, 250.0);
    this->m_store[LOCATION].valid = Fw::TlmValid::VALID;
    this->m_store[LOCATION].time = time;
    this->m_store[LOCATION].value.resetSer();
    ASSERT_EQ(this->m_store[LOCATION].value.serializeFrom(data), Fw::FW_SERIALIZE_OK);
}

void PiCameraTester::setNominal() {
    this->m_camera.reset();
    this->m_bufferAvailable = true;
    // The command arrives one second before the frame
    this->setTestTime(this->timeAt(-USEC_PER_SEC));
    this->m_camera.onFrame = [this]() { this->setTestTime(this->m_captureTime); };
    this->setTemperature(21.5F, this->timeAt(-100000));
    this->setAcceleration(0.0F, 0.0F, 9.81F, this->timeAt(-50000));
    this->setLocation(34.2013, -118.1714, this->timeAt(-900000));
}

// ----------------------------------------------------------------------
// Helpers: stimulus
// ----------------------------------------------------------------------

void PiCameraTester::dispatchAll() {
    while (this->component.m_queue.getMessagesAvailable() > 0) {
        ASSERT_EQ(this->component.doDispatch(), Fw::QueuedComponentBase::MSG_DISPATCH_OK);
    }
}

void PiCameraTester::capture() {
    this->clearHistory();
    this->m_camera.clearLog();
    this->m_cmdSeq++;
    this->sendCmd_CAPTURE(TEST_INSTANCE_ID, this->m_cmdSeq);
    this->dispatchAll();
}

void PiCameraTester::ping(U32 key) {
    this->clearHistory();
    this->invoke_to_pingIn(0, key);
    this->dispatchAll();
    ASSERT_from_pingOut_SIZE(1);
    ASSERT_from_pingOut(0, key);
}

// ----------------------------------------------------------------------
// Helpers: checks
// ----------------------------------------------------------------------

void PiCameraTester::assertCameraClosed() {
    ASSERT_GE(this->m_camera.logSize, 2U);
    ASSERT_EQ(this->m_camera.log[this->m_camera.logSize - 2], FakeCamera::STOP);
    ASSERT_EQ(this->m_camera.log[this->m_camera.logSize - 1], FakeCamera::CLOSE);
}

PiCameraTester::Product PiCameraTester::readProduct(U32 index) {
    Product product = {};
    EXPECT_LT(index, this->productSendHistory->size());
    Fw::Buffer buffer = this->productSendHistory->at(index).buffer;
    Fw::DpContainer container;
    container.setBuffer(buffer);
    EXPECT_EQ(container.deserializeHeader(), Fw::FW_SERIALIZE_OK);
    product.timeTag = container.getTimeTag();
    product.priority = container.getPriority();
    Fw::ExternalSerializeBuffer data(buffer.getData() + Fw::DpContainer::DATA_OFFSET, container.getDataSize());
    EXPECT_EQ(data.setBuffLen(container.getDataSize()), Fw::FW_SERIALIZE_OK);
    product.pictureMatches = true;
    while (data.getDeserializeSizeLeft() > 0) {
        FwDpIdType recordId = 0;
        EXPECT_EQ(data.deserializeTo(recordId), Fw::FW_SERIALIZE_OK);
        product.records++;
        if (recordId == this->component.getIdBase() + PiCamera::RecordId::Metrics) {
            product.metricsRecords++;
            EXPECT_EQ(data.deserializeTo(product.metrics), Fw::FW_SERIALIZE_OK);
        } else if (recordId == this->component.getIdBase() + PiCamera::RecordId::Picture) {
            product.pictureRecords++;
            FwSizeStoreType size = 0;
            EXPECT_EQ(data.deserializeTo(size), Fw::FW_SERIALIZE_OK);
            product.pictureSize = size;
            for (FwSizeType i = 0; i < size; i++) {
                U8 byte = 0;
                EXPECT_EQ(data.deserializeTo(byte), Fw::FW_SERIALIZE_OK);
                product.pictureMatches = product.pictureMatches && (byte == this->m_camera.fill);
            }
        } else {
            ADD_FAILURE() << "unknown record " << recordId;
            break;
        }
    }
    return product;
}

void PiCameraTester::assertSuccess(FwSizeType pictureSize) {
    ASSERT_CMD_RESPONSE_SIZE(1);
    ASSERT_CMD_RESPONSE(0, PiCamera::OPCODE_CAPTURE, this->m_cmdSeq, Fw::CmdResponse::OK);
    ASSERT_EVENTS_SIZE(2);
    ASSERT_EVENTS_CaptureStarted_SIZE(1);
    ASSERT_EVENTS_CaptureCompleted_SIZE(1);
    ASSERT_EVENTS_CaptureCompleted(0, static_cast<U32>(pictureSize));
    ASSERT_PRODUCT_GET_SIZE(1);
    ASSERT_PRODUCT_SEND_SIZE(1);
    const Product product = this->readProduct(0);
    ASSERT_EQ(product.records, 2U);
    ASSERT_EQ(product.metricsRecords, 1U);
    ASSERT_EQ(product.pictureRecords, 1U);
    ASSERT_EQ(product.pictureSize, pictureSize);
    ASSERT_TRUE(product.pictureMatches);
    this->assertCameraClosed();
    ASSERT_FALSE(this->component.m_busy);
}

void PiCameraTester::assertFailure(PiCamera_FailReason reason, PiCamera_FailStep step, I32 code) {
    ASSERT_CMD_RESPONSE_SIZE(1);
    ASSERT_CMD_RESPONSE(0, PiCamera::OPCODE_CAPTURE, this->m_cmdSeq, Fw::CmdResponse::EXECUTION_ERROR);
    ASSERT_EVENTS_CaptureFailed_SIZE(1);
    ASSERT_EVENTS_CaptureFailed(0, reason, step, code);
    ASSERT_EVENTS_CaptureCompleted_SIZE(0);
    ASSERT_PRODUCT_SEND_SIZE(0);
    ASSERT_TLM_CapturesCompleted_SIZE(0);
    ASSERT_TLM_LastPictureSize_SIZE(0);
    ASSERT_TLM_CapturesFailed_SIZE(1);
    this->assertCameraClosed();
    ASSERT_FALSE(this->component.m_busy);
}

void PiCameraTester::captureFails(PiCamera_FailReason reason, PiCamera_FailStep step, I32 code) {
    this->capture();
    this->assertFailure(reason, step, code);
    // REQ-PiCamera-019: with the cause removed the next capture succeeds
    this->setNominal();
    this->capture();
    this->assertSuccess(this->m_camera.jpegSize);
}

// ----------------------------------------------------------------------
// Tests
// ----------------------------------------------------------------------

void PiCameraTester::testNominalCapture() {
    this->m_camera.jpegSize = 54321;
    this->capture();
    this->assertSuccess(54321);
    ASSERT_PRODUCT_GET(0, this->component.getIdBase() + PiCamera::ContainerId::Capture,
                       Fw::DpContainer::MIN_PACKET_SIZE + PiCamera::SIZE_OF_Metrics_RECORD +
                           PiCamera::SIZE_OF_Picture_RECORD(54321));
    ASSERT_EQ(this->readProduct(0).priority, 10U);
    // The camera was asked for what the constants say
    ASSERT_EQ(this->m_camera.width, 640U);
    ASSERT_EQ(this->m_camera.height, 480U);
    ASSERT_EQ(this->m_camera.settleFrames, static_cast<U32>(PiCamera_SETTLE_FRAMES));
    ASSERT_EQ(this->m_camera.quality, static_cast<U32>(PiCamera_JPEG_QUALITY));
    ASSERT_EQ(this->m_camera.capacity, static_cast<FwSizeType>(PiCamera_PICTURE_MAX_SIZE));
}

void PiCameraTester::testMetricsCopied() {
    this->setTemperature(-12.25F, this->timeAt(-1));
    this->setLocation(-33.8688, 151.2093, this->timeAt(-2));
    this->capture();
    this->assertSuccess(this->m_camera.jpegSize);
    const Product product = this->readProduct(0);
    ASSERT_EQ(product.metrics.get_temperature(), -12.25F);
    ASSERT_EQ(product.metrics.get_latitude(), -33.8688);
    ASSERT_EQ(product.metrics.get_longitude(), 151.2093);
}

void PiCameraTester::testRollPitch() {
    struct Case {
        F32 x;
        F32 y;
        F32 z;
    };
    const Case cases[] = {{9.81F, 0.0F, 0.0F}, {-9.81F, 0.0F, 0.0F}, {0.0F, 9.81F, 0.0F}, {0.0F, -9.81F, 0.0F},
                          {0.0F, 0.0F, 9.81F}, {0.0F, 0.0F, -9.81F}, {1.5F, -2.5F, 9.0F}};
    for (const Case& c : cases) {
        this->setAcceleration(c.x, c.y, c.z, this->timeAt(0));
        this->capture();
        this->assertSuccess(this->m_camera.jpegSize);
        const Product product = this->readProduct(0);
        const F64 roll = std::atan2(static_cast<F64>(c.y), static_cast<F64>(c.z)) * 180.0 / PI;
        const F64 pitch = std::atan2(-static_cast<F64>(c.x), std::sqrt(static_cast<F64>(c.y) * c.y +
                                                                       static_cast<F64>(c.z) * c.z)) *
                          180.0 / PI;
        ASSERT_NEAR(product.metrics.get_roll(), roll, 0.01);
        ASSERT_NEAR(product.metrics.get_pitch(), pitch, 0.01);
    }
    // Fixed values, independent of the formula above
    this->setAcceleration(-9.81F, 0.0F, 0.0F, this->timeAt(0));
    this->capture();
    ASSERT_NEAR(this->readProduct(0).metrics.get_pitch(), 90.0, 0.01);
    this->setAcceleration(0.0F, 9.81F, 0.0F, this->timeAt(0));
    this->capture();
    ASSERT_NEAR(this->readProduct(0).metrics.get_roll(), 90.0, 0.01);
    this->setAcceleration(0.0F, 0.0F, -9.81F, this->timeAt(0));
    this->capture();
    ASSERT_NEAR(std::fabs(this->readProduct(0).metrics.get_roll()), 180.0, 0.01);
}

void PiCameraTester::testCaptureTime() {
    this->capture();
    this->assertSuccess(this->m_camera.jpegSize);
    const Product product = this->readProduct(0);
    // setNominal: the command time is one second before the time set at the frame
    ASSERT_EQ(product.timeTag, this->m_captureTime);
    ASSERT_EQ(product.metrics.get_captureTime(), this->m_captureTime.asTimeValue());
    ASSERT_NE(product.timeTag, this->timeAt(-USEC_PER_SEC));
}

void PiCameraTester::testSampleTimes() {
    this->setTemperature(20.0F, this->timeAt(-1500000));
    this->setAcceleration(0.0F, 0.0F, 9.81F, this->timeAt(-700));
    this->setLocation(10.0, 20.0, this->timeAt(1200000));
    this->capture();
    this->assertSuccess(this->m_camera.jpegSize);
    const Product product = this->readProduct(0);
    ASSERT_EQ(product.metrics.get_temperatureTime(), this->timeAt(-1500000).asTimeValue());
    ASSERT_EQ(product.metrics.get_attitudeTime(), this->timeAt(-700).asTimeValue());
    ASSERT_EQ(product.metrics.get_locationTime(), this->timeAt(1200000).asTimeValue());
}

void PiCameraTester::testFrameTimeout() {
    this->m_camera.status[FakeCamera::WAIT_FRAME] = Camera::Status::TIMEOUT;
    this->captureFails(PiCamera_FailReason::TIMEOUT, PiCamera_FailStep::FRAME, 0);
    ASSERT_EQ(this->m_camera.timeoutMs, static_cast<U32>(PiCamera_FRAME_TIMEOUT_MS));
}

void PiCameraTester::testStaleReading() {
    const PiCamera_FailStep steps[NUM_CHANNELS] = {PiCamera_FailStep::TEMPERATURE, PiCamera_FailStep::ATTITUDE,
                                                   PiCamera_FailStep::LOCATION};
    for (U32 channel = 0; channel < NUM_CHANNELS; channel++) {
        // At the limit, earlier and later: passes
        this->m_store[channel].time = this->timeAt(-MAX_AGE_USEC);
        this->capture();
        this->assertSuccess(this->m_camera.jpegSize);
        this->m_store[channel].time = this->timeAt(MAX_AGE_USEC);
        this->capture();
        this->assertSuccess(this->m_camera.jpegSize);
        // 1 ms beyond the limit, earlier and later: fails with the age
        this->m_store[channel].time = this->timeAt(-MAX_AGE_USEC - 1000);
        this->captureFails(PiCamera_FailReason::SENSOR_STALE, steps[channel], PiCamera_METRIC_MAX_AGE_MS + 1);
        this->m_store[channel].time = this->timeAt(MAX_AGE_USEC + 1000);
        this->captureFails(PiCamera_FailReason::SENSOR_STALE, steps[channel], -(PiCamera_METRIC_MAX_AGE_MS + 1));
        // Another time base: fails with code 0
        this->m_store[channel].time =
            Fw::Time(TimeBase::TB_PROC_TIME, this->m_captureTime.getSeconds(), this->m_captureTime.getUSeconds());
        this->captureFails(PiCamera_FailReason::SENSOR_STALE, steps[channel], 0);
        // An age beyond the I32 range: the range limit. The other readings carry the capture time.
        const Fw::Time early(TimeBase::TB_WORKSTATION_TIME, 0, 0);
        const Fw::Time late(TimeBase::TB_WORKSTATION_TIME, 4000000000U, 0);
        this->m_captureTime = late;
        for (U32 other = 0; other < NUM_CHANNELS; other++) {
            this->m_store[other].time = (other == channel) ? early : late;
        }
        this->capture();
        this->assertFailure(PiCamera_FailReason::SENSOR_STALE, steps[channel], std::numeric_limits<I32>::max());
        this->m_captureTime = early;
        for (U32 other = 0; other < NUM_CHANNELS; other++) {
            this->m_store[other].time = (other == channel) ? late : early;
        }
        this->capture();
        this->assertFailure(PiCamera_FailReason::SENSOR_STALE, steps[channel], std::numeric_limits<I32>::min());
        this->m_captureTime = Fw::Time(TimeBase::TB_WORKSTATION_TIME, CAPTURE_SECONDS, 500000);
        this->setNominal();
    }
}

void PiCameraTester::testMissingReading() {
    const PiCamera_FailStep steps[NUM_CHANNELS] = {PiCamera_FailStep::TEMPERATURE, PiCamera_FailStep::ATTITUDE,
                                                   PiCamera_FailStep::LOCATION};
    for (U32 channel = 0; channel < NUM_CHANNELS; channel++) {
        this->m_store[channel].valid = Fw::TlmValid::INVALID;
        this->captureFails(PiCamera_FailReason::SENSOR_NO_DATA, steps[channel], 0);
        this->m_store[channel].value.resetSer();
        this->captureFails(PiCamera_FailReason::SENSOR_NO_DATA, steps[channel], 0);
        ASSERT_EQ(this->m_store[channel].value.setBuffLen(this->m_store[channel].value.getSize() - 1),
                  Fw::FW_SERIALIZE_OK);
        this->captureFails(PiCamera_FailReason::SENSOR_NO_DATA, steps[channel], 0);
        // Stale and too short to decode: the decode is checked first
        ASSERT_EQ(this->m_store[channel].value.setBuffLen(this->m_store[channel].value.getSize() - 1),
                  Fw::FW_SERIALIZE_OK);
        this->m_store[channel].time = this->timeAt(-10 * USEC_PER_SEC);
        this->captureFails(PiCamera_FailReason::SENSOR_NO_DATA, steps[channel], 0);
    }
}

void PiCameraTester::testInvalidMetric() {
    const F32 nan = std::numeric_limits<F32>::quiet_NaN();
    const F32 inf = std::numeric_limits<F32>::infinity();
    const F64 nan64 = std::numeric_limits<F64>::quiet_NaN();
    const F64 inf64 = std::numeric_limits<F64>::infinity();
    const Fw::Time now = this->timeAt(0);
    const PiCamera_FailReason invalid = PiCamera_FailReason::METRIC_INVALID;

    for (const F32 bad : {nan, inf, -inf}) {
        this->setTemperature(bad, now);
        this->captureFails(invalid, PiCamera_FailStep::TEMPERATURE, 0);
        this->setAcceleration(bad, 0.0F, 9.81F, now);
        this->captureFails(invalid, PiCamera_FailStep::ATTITUDE, 0);
        this->setAcceleration(0.0F, bad, 9.81F, now);
        this->captureFails(invalid, PiCamera_FailStep::ATTITUDE, 0);
        this->setAcceleration(0.0F, 0.0F, bad, now);
        this->captureFails(invalid, PiCamera_FailStep::ATTITUDE, 0);
    }
    this->setAcceleration(0.0F, 0.0F, 0.0F, now);
    this->captureFails(invalid, PiCamera_FailStep::ATTITUDE, 0);

    for (const F64 bad : {nan64, inf64, -inf64, std::nextafter(90.0, 91.0), std::nextafter(-90.0, -91.0)}) {
        this->setLocation(bad, 0.0, now);
        this->captureFails(invalid, PiCamera_FailStep::LOCATION, 0);
    }
    for (const F64 bad : {nan64, inf64, -inf64, std::nextafter(180.0, 181.0), std::nextafter(-180.0, -181.0)}) {
        this->setLocation(0.0, bad, now);
        this->captureFails(invalid, PiCamera_FailStep::LOCATION, 0);
    }
    // The limits pass
    for (const F64 latitude : {90.0, -90.0}) {
        for (const F64 longitude : {180.0, -180.0}) {
            this->setLocation(latitude, longitude, now);
            this->capture();
            this->assertSuccess(this->m_camera.jpegSize);
            ASSERT_EQ(this->readProduct(0).metrics.get_latitude(), latitude);
            ASSERT_EQ(this->readProduct(0).metrics.get_longitude(), longitude);
        }
    }
}

void PiCameraTester::testNoCamera() {
    this->m_camera.status[FakeCamera::DETECT] = Camera::Status::NO_CAMERA;
    this->capture();
    this->assertFailure(PiCamera_FailReason::NO_CAMERA, PiCamera_FailStep::DETECT, 0);
    // No later step ran
    ASSERT_EQ(this->m_camera.count[FakeCamera::OPEN], 0U);
    ASSERT_from_tlmGetOut_SIZE(0);
    ASSERT_PRODUCT_GET_SIZE(0);
}

void PiCameraTester::testCameraErrors() {
    const FakeCamera::Call calls[] = {FakeCamera::DETECT, FakeCamera::OPEN, FakeCamera::CONFIGURE,
                                      FakeCamera::START,  FakeCamera::WAIT_FRAME, FakeCamera::ENCODE};
    const PiCamera_FailStep steps[] = {PiCamera_FailStep::DETECT, PiCamera_FailStep::OPEN,
                                       PiCamera_FailStep::CONFIGURE, PiCamera_FailStep::START,
                                       PiCamera_FailStep::FRAME,  PiCamera_FailStep::ENCODE};
    for (U32 i = 0; i < FW_NUM_ARRAY_ELEMENTS(calls); i++) {
        const I32 code = -static_cast<I32>(STest::Pick::lowerUpper(1, 200));
        this->m_camera.status[calls[i]] = Camera::Status::ERROR;
        this->m_camera.code[calls[i]] = code;
        this->capture();
        this->assertFailure(PiCamera_FailReason::CAMERA_ERROR, steps[i], code);
        // No later camera call ran, except stop and close
        for (U32 later = i + 1; later < FW_NUM_ARRAY_ELEMENTS(calls); later++) {
            ASSERT_EQ(this->m_camera.count[calls[later]], 0U);
        }
        ASSERT_PRODUCT_GET_SIZE(0);
        this->setNominal();
        this->capture();
        this->assertSuccess(this->m_camera.jpegSize);
    }
    // An encode that reports success and no bytes
    this->m_camera.jpegSize = 0;
    this->captureFails(PiCamera_FailReason::CAMERA_ERROR, PiCamera_FailStep::ENCODE, 0);
}

void PiCameraTester::testTooLarge() {
    this->m_camera.jpegSize = PiCamera_PICTURE_MAX_SIZE;
    this->capture();
    this->assertSuccess(PiCamera_PICTURE_MAX_SIZE);
    ASSERT_TLM_LastPictureSize(0, static_cast<U32>(PiCamera_PICTURE_MAX_SIZE));
    this->m_camera.jpegSize = PiCamera_PICTURE_MAX_SIZE + 1;
    this->captureFails(PiCamera_FailReason::TOO_LARGE, PiCamera_FailStep::ENCODE, 0);
}

void PiCameraTester::testNoContainer() {
    this->m_bufferAvailable = false;
    this->capture();
    this->assertFailure(PiCamera_FailReason::NO_CONTAINER, PiCamera_FailStep::CONTAINER, 0);
    ASSERT_PRODUCT_GET_SIZE(1);
    this->setNominal();
    this->capture();
    this->assertSuccess(this->m_camera.jpegSize);
}

void PiCameraTester::testFailureResponse() {
    // One failure of each kind: assertFailure checks one EXECUTION_ERROR response, one
    // CaptureFailed, no CaptureCompleted and no container for each
    this->m_camera.status[FakeCamera::DETECT] = Camera::Status::NO_CAMERA;
    this->captureFails(PiCamera_FailReason::NO_CAMERA, PiCamera_FailStep::DETECT, 0);
    this->m_camera.status[FakeCamera::START] = Camera::Status::ERROR;
    this->m_camera.code[FakeCamera::START] = -5;
    this->captureFails(PiCamera_FailReason::CAMERA_ERROR, PiCamera_FailStep::START, -5);
    this->m_camera.status[FakeCamera::WAIT_FRAME] = Camera::Status::TIMEOUT;
    this->captureFails(PiCamera_FailReason::TIMEOUT, PiCamera_FailStep::FRAME, 0);
    this->m_camera.jpegSize = PiCamera_PICTURE_MAX_SIZE + 1;
    this->captureFails(PiCamera_FailReason::TOO_LARGE, PiCamera_FailStep::ENCODE, 0);
    this->m_store[LOCATION].valid = Fw::TlmValid::INVALID;
    this->captureFails(PiCamera_FailReason::SENSOR_NO_DATA, PiCamera_FailStep::LOCATION, 0);
    this->m_store[LOCATION].time = this->timeAt(-60 * USEC_PER_SEC);
    this->captureFails(PiCamera_FailReason::SENSOR_STALE, PiCamera_FailStep::LOCATION, 60000);
    this->setAcceleration(0.0F, 0.0F, 0.0F, this->timeAt(0));
    this->captureFails(PiCamera_FailReason::METRIC_INVALID, PiCamera_FailStep::ATTITUDE, 0);
    this->m_bufferAvailable = false;
    this->captureFails(PiCamera_FailReason::NO_CONTAINER, PiCamera_FailStep::CONTAINER, 0);
}

void PiCameraTester::testBusyDuringCapture() {
    // Reference: the container of a capture nobody disturbs
    this->capture();
    this->assertSuccess(this->m_camera.jpegSize);
    const Product reference = this->readProduct(0);

    // A second command arrives while the camera is being detected
    const U32 busySeq = 7777;
    this->m_camera.onDetect = [this, busySeq]() {
        ASSERT_TRUE(this->component.m_busy);
        this->sendCmd_CAPTURE(TEST_INSTANCE_ID, busySeq);
    };
    this->capture();
    ASSERT_CMD_RESPONSE_SIZE(2);
    ASSERT_CMD_RESPONSE(0, PiCamera::OPCODE_CAPTURE, busySeq, Fw::CmdResponse::EXECUTION_ERROR);
    ASSERT_CMD_RESPONSE(1, PiCamera::OPCODE_CAPTURE, this->m_cmdSeq, Fw::CmdResponse::OK);
    ASSERT_EVENTS_CaptureFailed_SIZE(1);
    ASSERT_EVENTS_CaptureFailed(0, PiCamera_FailReason::BUSY, PiCamera_FailStep::RECEIVE, 0);
    ASSERT_EVENTS_CaptureStarted_SIZE(1);
    ASSERT_EVENTS_CaptureCompleted_SIZE(1);
    ASSERT_TLM_CapturesFailed_SIZE(1);
    ASSERT_TLM_CapturesFailed(0, 1);
    ASSERT_TLM_CapturesCompleted(0, 2);
    // One capture ran, with the same container as without the second command
    ASSERT_EQ(this->m_camera.count[FakeCamera::DETECT], 1U);
    ASSERT_PRODUCT_SEND_SIZE(1);
    const Product product = this->readProduct(0);
    ASSERT_EQ(product.metrics, reference.metrics);
    ASSERT_EQ(product.pictureSize, reference.pictureSize);
    ASSERT_EQ(product.timeTag, reference.timeTag);

    // A command sent from inside the response of the earlier capture is accepted
    this->m_camera.onDetect = nullptr;
    const U32 nextSeq = 8888;
    this->m_onResponse = [this, nextSeq]() {
        this->m_onResponse = nullptr;
        this->sendCmd_CAPTURE(TEST_INSTANCE_ID, nextSeq);
    };
    this->capture();
    ASSERT_CMD_RESPONSE_SIZE(2);
    ASSERT_CMD_RESPONSE(0, PiCamera::OPCODE_CAPTURE, this->m_cmdSeq, Fw::CmdResponse::OK);
    ASSERT_CMD_RESPONSE(1, PiCamera::OPCODE_CAPTURE, nextSeq, Fw::CmdResponse::OK);
    ASSERT_EVENTS_CaptureStarted_SIZE(2);
    ASSERT_EVENTS_CaptureCompleted_SIZE(2);
    ASSERT_EVENTS_CaptureFailed_SIZE(0);
    ASSERT_PRODUCT_SEND_SIZE(2);
}

void PiCameraTester::testRecoveryAfterFailure() {
    // captureFails ends each case with a capture that succeeds once the cause is removed
    this->m_camera.status[FakeCamera::DETECT] = Camera::Status::NO_CAMERA;
    this->captureFails(PiCamera_FailReason::NO_CAMERA, PiCamera_FailStep::DETECT, 0);
    this->m_camera.status[FakeCamera::OPEN] = Camera::Status::ERROR;
    this->m_camera.code[FakeCamera::OPEN] = -16;
    this->captureFails(PiCamera_FailReason::CAMERA_ERROR, PiCamera_FailStep::OPEN, -16);
    this->m_camera.status[FakeCamera::WAIT_FRAME] = Camera::Status::TIMEOUT;
    this->captureFails(PiCamera_FailReason::TIMEOUT, PiCamera_FailStep::FRAME, 0);
    this->m_camera.jpegSize = PiCamera_PICTURE_MAX_SIZE + 1;
    this->captureFails(PiCamera_FailReason::TOO_LARGE, PiCamera_FailStep::ENCODE, 0);
    this->m_store[TEMPERATURE].valid = Fw::TlmValid::INVALID;
    this->captureFails(PiCamera_FailReason::SENSOR_NO_DATA, PiCamera_FailStep::TEMPERATURE, 0);
    this->m_store[ATTITUDE].time = this->timeAt(-3 * USEC_PER_SEC);
    this->captureFails(PiCamera_FailReason::SENSOR_STALE, PiCamera_FailStep::ATTITUDE, 3000);
    this->setLocation(91.0, 0.0, this->timeAt(0));
    this->captureFails(PiCamera_FailReason::METRIC_INVALID, PiCamera_FailStep::LOCATION, 0);
    this->m_bufferAvailable = false;
    this->captureFails(PiCamera_FailReason::NO_CONTAINER, PiCamera_FailStep::CONTAINER, 0);
    // BUSY: the command after the busy one succeeds
    this->m_camera.onDetect = [this]() { this->sendCmd_CAPTURE(TEST_INSTANCE_ID, 1); };
    this->capture();
    ASSERT_EVENTS_CaptureFailed(0, PiCamera_FailReason::BUSY, PiCamera_FailStep::RECEIVE, 0);
    this->setNominal();
    this->capture();
    this->assertSuccess(this->m_camera.jpegSize);
}

void PiCameraTester::testEvents() {
    // CaptureStarted is emitted before the first camera call
    bool startedBeforeCamera = false;
    this->m_camera.onDetect = [this, &startedBeforeCamera]() {
        startedBeforeCamera = (this->eventsSize_CaptureStarted == 1) && (this->m_camera.logSize == 0);
    };
    this->m_camera.jpegSize = 4242;
    this->capture();
    ASSERT_TRUE(startedBeforeCamera);
    this->assertSuccess(4242);
    // A failed capture also starts once and does not complete
    this->m_camera.status[FakeCamera::OPEN] = Camera::Status::ERROR;
    this->capture();
    ASSERT_EVENTS_SIZE(2);
    ASSERT_EVENTS_CaptureStarted_SIZE(1);
    ASSERT_EVENTS_CaptureFailed_SIZE(1);
    ASSERT_EVENTS_CaptureCompleted_SIZE(0);
}

void PiCameraTester::testTelemetryOnChange() {
    this->clearHistory();
    this->component.preamble();
    ASSERT_TLM_SIZE(3);
    ASSERT_TLM_CapturesCompleted(0, 0);
    ASSERT_TLM_CapturesFailed(0, 0);
    ASSERT_TLM_LastPictureSize(0, 0);

    this->m_camera.jpegSize = 2048;
    this->capture();
    ASSERT_TLM_SIZE(2);
    ASSERT_TLM_CapturesCompleted(0, 1);
    ASSERT_TLM_LastPictureSize(0, 2048);

    this->m_camera.status[FakeCamera::DETECT] = Camera::Status::NO_CAMERA;
    this->capture();
    ASSERT_TLM_SIZE(1);
    ASSERT_TLM_CapturesFailed(0, 1);

    this->setNominal();
    this->m_camera.jpegSize = 4096;
    this->capture();
    ASSERT_TLM_SIZE(2);
    ASSERT_TLM_CapturesCompleted(0, 2);
    ASSERT_TLM_LastPictureSize(0, 4096);
}

void PiCameraTester::testPing() {
    this->ping(0);
    this->ping(STest::Pick::any());
    this->ping(0xFFFFFFFFU);
}

// ----------------------------------------------------------------------
// Rules for random sequences
// ----------------------------------------------------------------------

bool PiCameraTester::Capture__Nominal__precondition() const {
    return true;
}

void PiCameraTester::Capture__Nominal__action() {
    this->setNominal();
    this->m_camera.jpegSize = STest::Pick::lowerUpper(1, PiCamera_PICTURE_MAX_SIZE);
    this->capture();
    this->assertSuccess(this->m_camera.jpegSize);
    this->m_expectedCompleted++;
    this->m_commands++;
    this->m_responses += static_cast<U32>(this->cmdResponseHistory->size());
    ASSERT_TLM_CapturesCompleted(0, this->m_expectedCompleted);
    ASSERT_TLM_CapturesFailed_SIZE(0);
}

bool PiCameraTester::Capture__Busy__precondition() const {
    return true;
}

void PiCameraTester::Capture__Busy__action() {
    this->setNominal();
    const U32 extra = STest::Pick::lowerUpper(1, 3);
    this->m_camera.onDetect = [this, extra]() {
        for (U32 i = 0; i < extra; i++) {
            this->sendCmd_CAPTURE(TEST_INSTANCE_ID, 100000 + i);
        }
    };
    this->capture();
    this->m_expectedCompleted++;
    this->m_expectedFailed += extra;
    this->m_commands += extra + 1;
    this->m_responses += static_cast<U32>(this->cmdResponseHistory->size());
    ASSERT_CMD_RESPONSE_SIZE(extra + 1);
    ASSERT_CMD_RESPONSE(extra, PiCamera::OPCODE_CAPTURE, this->m_cmdSeq, Fw::CmdResponse::OK);
    ASSERT_EVENTS_CaptureFailed_SIZE(extra);
    ASSERT_PRODUCT_SEND_SIZE(1);
    ASSERT_TLM_CapturesFailed_SIZE(extra);
    ASSERT_TLM_CapturesFailed(extra - 1, this->m_expectedFailed);
    ASSERT_TLM_CapturesCompleted(0, this->m_expectedCompleted);
}

bool PiCameraTester::Capture__CameraFailure__precondition() const {
    return true;
}

void PiCameraTester::Capture__CameraFailure__action() {
    this->setNominal();
    const FakeCamera::Call call = static_cast<FakeCamera::Call>(STest::Pick::lowerUpper(FakeCamera::DETECT,
                                                                                         FakeCamera::ENCODE));
    const PiCamera_FailStep steps[] = {PiCamera_FailStep::DETECT, PiCamera_FailStep::OPEN,
                                       PiCamera_FailStep::CONFIGURE, PiCamera_FailStep::START,
                                       PiCamera_FailStep::FRAME,  PiCamera_FailStep::ENCODE};
    this->m_camera.status[call] = Camera::Status::ERROR;
    this->m_camera.code[call] = -1;
    this->capture();
    this->assertFailure(PiCamera_FailReason::CAMERA_ERROR, steps[call], -1);
    this->m_expectedFailed++;
    this->m_commands++;
    this->m_responses += static_cast<U32>(this->cmdResponseHistory->size());
    ASSERT_TLM_CapturesFailed(0, this->m_expectedFailed);
}

bool PiCameraTester::Capture__SensorFailure__precondition() const {
    return true;
}

void PiCameraTester::Capture__SensorFailure__action() {
    this->setNominal();
    const U32 channel = STest::Pick::lowerUpper(0, NUM_CHANNELS - 1);
    const PiCamera_FailStep steps[NUM_CHANNELS] = {PiCamera_FailStep::TEMPERATURE, PiCamera_FailStep::ATTITUDE,
                                                   PiCamera_FailStep::LOCATION};
    this->m_store[channel].valid = Fw::TlmValid::INVALID;
    this->capture();
    this->assertFailure(PiCamera_FailReason::SENSOR_NO_DATA, steps[channel], 0);
    this->m_expectedFailed++;
    this->m_commands++;
    this->m_responses += static_cast<U32>(this->cmdResponseHistory->size());
    ASSERT_TLM_CapturesFailed(0, this->m_expectedFailed);
}

bool PiCameraTester::Capture__NoBuffer__precondition() const {
    return true;
}

void PiCameraTester::Capture__NoBuffer__action() {
    this->setNominal();
    this->m_bufferAvailable = false;
    this->capture();
    this->assertFailure(PiCamera_FailReason::NO_CONTAINER, PiCamera_FailStep::CONTAINER, 0);
    this->m_expectedFailed++;
    this->m_commands++;
    this->m_responses += static_cast<U32>(this->cmdResponseHistory->size());
    ASSERT_TLM_CapturesFailed(0, this->m_expectedFailed);
}

bool PiCameraTester::Health__Ping__precondition() const {
    return true;
}

void PiCameraTester::Health__Ping__action() {
    this->ping(STest::Pick::any());
}

void PiCameraTester::testRandomSequences() {
    Capture__Nominal nominal;
    Capture__Busy busy;
    Capture__CameraFailure cameraFailure;
    Capture__SensorFailure sensorFailure;
    Capture__NoBuffer noBuffer;
    Health__Ping pingRule;
    STest::Rule<PiCameraTester>* rules[] = {&nominal, &busy, &cameraFailure, &sensorFailure, &noBuffer, &pingRule};
    STest::RandomScenario<PiCameraTester> random("Random", rules, FW_NUM_ARRAY_ELEMENTS(rules));
    STest::BoundedScenario<PiCameraTester> bounded("Bounded", random, 1000);
    const U32 steps = bounded.run(*this);
    ASSERT_EQ(steps, 1000U);
    // One response per command, and the counts equal the responses
    ASSERT_EQ(this->m_responses, this->m_commands);
    ASSERT_EQ(this->component.m_completed + this->component.m_failed, this->m_responses);
    ASSERT_EQ(this->component.m_completed, this->m_expectedCompleted);
    ASSERT_EQ(this->component.m_failed, this->m_expectedFailed);
}

}  // namespace PiSensor
