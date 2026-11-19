// ======================================================================
// \title  PiCamera.cpp
// \brief  cpp file for PiCamera component implementation class
// ======================================================================

#include "Components/PiCamera/PiCamera.hpp"

#include <cmath>
#include <limits>

#include "fprime-sensors/Bmp280/Types/Bmp280DataSerializableAc.hpp"
#include "fprime-sensors/MpuImu/Types/ImuDataSerializableAc.hpp"
#include "fprime-sensors/NmeaGps/Types/GpsDataSerializableAc.hpp"

namespace PiSensor {

namespace {
constexpr F64 DEGREES_PER_RADIAN = 57.29577951308232;
constexpr I64 USEC_PER_SEC = 1000000;
constexpr I64 USEC_PER_MSEC = 1000;
}  // namespace

// ----------------------------------------------------------------------
// Component construction and destruction
// ----------------------------------------------------------------------

PiCamera::PiCamera(const char* const compName)
    : PiCameraComponentBase(compName),
      m_camera(nullptr),
      m_temperatureChannel(0),
      m_attitudeChannel(0),
      m_locationChannel(0),
      m_busy(false),
      m_completed(0),
      m_failed(0),
      m_jpeg{} {}

PiCamera::~PiCamera() {}

void PiCamera::configure(Camera& camera,
                         FwChanIdType temperatureChannel,
                         FwChanIdType attitudeChannel,
                         FwChanIdType locationChannel) {
    this->m_camera = &camera;
    this->m_temperatureChannel = temperatureChannel;
    this->m_attitudeChannel = attitudeChannel;
    this->m_locationChannel = locationChannel;
}

void PiCamera::preamble() {
    this->lock();
    this->tlmWrite_CapturesCompleted(this->m_completed);
    this->tlmWrite_CapturesFailed(this->m_failed);
    this->tlmWrite_LastPictureSize(0);
    this->unLock();
}

// ----------------------------------------------------------------------
// Handler implementations
// ----------------------------------------------------------------------

void PiCamera::pingIn_handler(FwIndexType portNum, U32 key) {
    this->pingOut_out(0, key);
}

void PiCamera::CAPTURE_cmdHandler(FwOpcodeType opCode, U32 cmdSeq) {
    // Guarded command: the component guard is held
    if (this->m_busy) {
        this->log_WARNING_HI_CaptureFailed(PiCamera_FailReason::BUSY, PiCamera_FailStep::RECEIVE, 0);
        this->m_failed++;
        this->tlmWrite_CapturesFailed(this->m_failed);
        this->cmdResponse_out(opCode, cmdSeq, Fw::CmdResponse::EXECUTION_ERROR);
        return;
    }
    this->m_busy = true;
    this->log_ACTIVITY_LO_CaptureStarted();
    this->acquire_internalInterfaceInvoke(opCode, cmdSeq);
}

void PiCamera::acquire_internalInterfaceHandler(FwOpcodeType opCode, U32 cmdSeq) {
    FW_ASSERT(this->m_camera != nullptr);
    Fw::Time captureTime;
    PiCamera_CaptureMetrics metrics;
    FwSizeType size = 0;

    StepResult result = this->acquireFrame();
    if (result.ok) {
        captureTime = this->getTime();
        result = this->readMetrics(captureTime, metrics);
    }
    if (result.ok) {
        result = this->encode(size);
    }
    // The camera is closed outside a capture, on success and on failure
    this->m_camera->stop();
    this->m_camera->close();
    if (result.ok) {
        result = this->store(captureTime, metrics, size);
    }

    if (result.ok) {
        this->log_ACTIVITY_HI_CaptureCompleted(static_cast<U32>(size));
    } else {
        this->log_WARNING_HI_CaptureFailed(result.reason, result.step, result.code);
    }
    this->endCapture(result.ok, static_cast<U32>(size));
    this->cmdResponse_out(opCode, cmdSeq, result.ok ? Fw::CmdResponse::OK : Fw::CmdResponse::EXECUTION_ERROR);
}

// ----------------------------------------------------------------------
// Steps of a capture
// ----------------------------------------------------------------------

PiCamera::StepResult PiCamera::acquireFrame() {
    // Each call is a statement of its own: it writes code before cameraResult reads it
    I32 code = 0;
    Camera::Status status = this->m_camera->detect(code);
    StepResult result = cameraResult(status, PiCamera_FailStep::DETECT, code);
    if (result.ok) {
        code = 0;
        status = this->m_camera->open(code);
        result = cameraResult(status, PiCamera_FailStep::OPEN, code);
    }
    if (result.ok) {
        code = 0;
        status = this->m_camera->configure(PiCamera_PICTURE_WIDTH, PiCamera_PICTURE_HEIGHT, code);
        result = cameraResult(status, PiCamera_FailStep::CONFIGURE, code);
    }
    if (result.ok) {
        code = 0;
        status = this->m_camera->start(code);
        result = cameraResult(status, PiCamera_FailStep::START, code);
    }
    if (result.ok) {
        code = 0;
        status = this->m_camera->waitFrame(PiCamera_FRAME_TIMEOUT_MS, PiCamera_SETTLE_FRAMES, code);
        result = cameraResult(status, PiCamera_FailStep::FRAME, code);
    }
    return result;
}

PiCamera::StepResult PiCamera::readChannel(FwChanIdType channel,
                                           PiCamera_FailStep step,
                                           const Fw::Time& captureTime,
                                           Fw::Time& sampleTime,
                                           Fw::TlmBuffer& value) {
    value.resetSer();
    const Fw::TlmValid valid = this->tlmGetOut_out(0, channel, sampleTime, value);
    if ((valid != Fw::TlmValid::VALID) || (value.getSize() == 0)) {
        return failure(PiCamera_FailReason::SENSOR_NO_DATA, step, 0);
    }
    if (sampleTime.getTimeBase() != captureTime.getTimeBase()) {
        return failure(PiCamera_FailReason::SENSOR_STALE, step, 0);
    }
    const I64 ageUsec =
        (static_cast<I64>(captureTime.getSeconds()) - static_cast<I64>(sampleTime.getSeconds())) * USEC_PER_SEC +
        (static_cast<I64>(captureTime.getUSeconds()) - static_cast<I64>(sampleTime.getUSeconds()));
    const I64 limitUsec = static_cast<I64>(PiCamera_METRIC_MAX_AGE_MS) * USEC_PER_MSEC;
    if ((ageUsec > limitUsec) || (ageUsec < -limitUsec)) {
        // |age| is at most 2^32 s, so the division result always fits I64; limit it to I32
        I64 ageMsec = ageUsec / USEC_PER_MSEC;
        ageMsec = FW_MIN(ageMsec, static_cast<I64>(std::numeric_limits<I32>::max()));
        ageMsec = FW_MAX(ageMsec, static_cast<I64>(std::numeric_limits<I32>::min()));
        return failure(PiCamera_FailReason::SENSOR_STALE, step, static_cast<I32>(ageMsec));
    }
    return success();
}

PiCamera::StepResult PiCamera::readMetrics(const Fw::Time& captureTime, PiCamera_CaptureMetrics& metrics) {
    Fw::TlmBuffer value;
    Fw::Time sampleTime;
    metrics.set_captureTime(captureTime.asTimeValue());

    // Temperature
    StepResult result =
        this->readChannel(this->m_temperatureChannel, PiCamera_FailStep::TEMPERATURE, captureTime, sampleTime, value);
    if (!result.ok) {
        return result;
    }
    Bmp280::Bmp280Data bmp;
    if (value.deserializeTo(bmp) != Fw::FW_SERIALIZE_OK) {
        return failure(PiCamera_FailReason::SENSOR_NO_DATA, PiCamera_FailStep::TEMPERATURE, 0);
    }
    if (!std::isfinite(bmp.get_temperature())) {
        return failure(PiCamera_FailReason::METRIC_INVALID, PiCamera_FailStep::TEMPERATURE, 0);
    }
    metrics.set_temperature(bmp.get_temperature());
    metrics.set_temperatureTime(sampleTime.asTimeValue());

    // Attitude
    result = this->readChannel(this->m_attitudeChannel, PiCamera_FailStep::ATTITUDE, captureTime, sampleTime, value);
    if (!result.ok) {
        return result;
    }
    MpuImu::ImuData imu;
    if (value.deserializeTo(imu) != Fw::FW_SERIALIZE_OK) {
        return failure(PiCamera_FailReason::SENSOR_NO_DATA, PiCamera_FailStep::ATTITUDE, 0);
    }
    const F32 ax = imu.get_acceleration().get_x();
    const F32 ay = imu.get_acceleration().get_y();
    const F32 az = imu.get_acceleration().get_z();
    const bool finite = std::isfinite(ax) && std::isfinite(ay) && std::isfinite(az);
    const bool zero = (ax == 0.0F) && (ay == 0.0F) && (az == 0.0F);
    if ((!finite) || zero) {
        return failure(PiCamera_FailReason::METRIC_INVALID, PiCamera_FailStep::ATTITUDE, 0);
    }
    metrics.set_roll(roll(ax, ay, az));
    metrics.set_pitch(pitch(ax, ay, az));
    metrics.set_attitudeTime(sampleTime.asTimeValue());

    // Location
    result = this->readChannel(this->m_locationChannel, PiCamera_FailStep::LOCATION, captureTime, sampleTime, value);
    if (!result.ok) {
        return result;
    }
    NmeaGps::GpsData gps;
    if (value.deserializeTo(gps) != Fw::FW_SERIALIZE_OK) {
        return failure(PiCamera_FailReason::SENSOR_NO_DATA, PiCamera_FailStep::LOCATION, 0);
    }
    const F64 latitude = gps.get_latitude();
    const F64 longitude = gps.get_longitude();
    // Comparisons with NaN are false, so the range check also rejects it
    const bool inRange = (latitude >= -90.0) && (latitude <= 90.0) && (longitude >= -180.0) && (longitude <= 180.0);
    if (!inRange) {
        return failure(PiCamera_FailReason::METRIC_INVALID, PiCamera_FailStep::LOCATION, 0);
    }
    metrics.set_latitude(latitude);
    metrics.set_longitude(longitude);
    metrics.set_locationTime(sampleTime.asTimeValue());
    return success();
}

PiCamera::StepResult PiCamera::encode(FwSizeType& size) {
    I32 code = 0;
    const Camera::Status status =
        this->m_camera->encode(PiCamera_JPEG_QUALITY, this->m_jpeg, sizeof(this->m_jpeg), size, code);
    StepResult result = cameraResult(status, PiCamera_FailStep::ENCODE, code);
    if (result.ok && ((size == 0) || (size > sizeof(this->m_jpeg)))) {
        // A camera interface that reports a size outside the destination
        result = (size == 0) ? failure(PiCamera_FailReason::CAMERA_ERROR, PiCamera_FailStep::ENCODE, 0)
                             : failure(PiCamera_FailReason::TOO_LARGE, PiCamera_FailStep::ENCODE, 0);
    }
    if (!result.ok) {
        size = 0;
    }
    return result;
}

PiCamera::StepResult PiCamera::store(const Fw::Time& captureTime,
                                     const PiCamera_CaptureMetrics& metrics,
                                     FwSizeType size) {
    DpContainer container;
    const FwSizeType dataSize = SIZE_OF_Metrics_RECORD + SIZE_OF_Picture_RECORD(size);
    if (this->dpGet_Capture(dataSize, container) != Fw::Success::SUCCESS) {
        return failure(PiCamera_FailReason::NO_CONTAINER, PiCamera_FailStep::CONTAINER, 0);
    }
    // The buffer was asked for these two records
    Fw::SerializeStatus status = container.serializeRecord_Metrics(metrics);
    FW_ASSERT(status == Fw::FW_SERIALIZE_OK, static_cast<FwAssertArgType>(status));
    status = container.serializeRecord_Picture(this->m_jpeg, size);
    FW_ASSERT(status == Fw::FW_SERIALIZE_OK, static_cast<FwAssertArgType>(status));
    this->dpSend(container, captureTime);
    return success();
}

void PiCamera::endCapture(bool success, U32 size) {
    this->lock();
    if (success) {
        this->m_completed++;
        this->tlmWrite_CapturesCompleted(this->m_completed);
        this->tlmWrite_LastPictureSize(size);
    } else {
        this->m_failed++;
        this->tlmWrite_CapturesFailed(this->m_failed);
    }
    this->m_busy = false;
    this->unLock();
}

// ----------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------

PiCamera::StepResult PiCamera::cameraResult(Camera::Status status, PiCamera_FailStep step, I32 code) {
    switch (status) {
        case Camera::Status::OK:
            return success();
        case Camera::Status::NO_CAMERA:
            return failure(PiCamera_FailReason::NO_CAMERA, step, code);
        case Camera::Status::TIMEOUT:
            return failure(PiCamera_FailReason::TIMEOUT, step, code);
        case Camera::Status::TOO_LARGE:
            return failure(PiCamera_FailReason::TOO_LARGE, step, code);
        case Camera::Status::ERROR:
        default:
            return failure(PiCamera_FailReason::CAMERA_ERROR, step, code);
    }
}

PiCamera::StepResult PiCamera::failure(PiCamera_FailReason reason, PiCamera_FailStep step, I32 code) {
    return StepResult{false, reason, step, code};
}

PiCamera::StepResult PiCamera::success() {
    return StepResult{true, PiCamera_FailReason::BUSY, PiCamera_FailStep::RECEIVE, 0};
}

F32 PiCamera::roll(F32 ax, F32 ay, F32 az) {
    static_cast<void>(ax);
    return static_cast<F32>(std::atan2(static_cast<F64>(ay), static_cast<F64>(az)) * DEGREES_PER_RADIAN);
}

F32 PiCamera::pitch(F32 ax, F32 ay, F32 az) {
    const F64 y = static_cast<F64>(ay);
    const F64 z = static_cast<F64>(az);
    return static_cast<F32>(std::atan2(-static_cast<F64>(ax), std::sqrt(y * y + z * z)) * DEGREES_PER_RADIAN);
}

}  // namespace PiSensor
