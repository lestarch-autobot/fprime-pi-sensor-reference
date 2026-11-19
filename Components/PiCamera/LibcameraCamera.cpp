// ======================================================================
// \title  LibcameraCamera.cpp
// \brief  Camera interface on libcamera and libjpeg (Raspberry Pi OS packages)
//
// This file is compiled as C++17, which the libcamera headers need. The
// libraries allocate memory and start threads of their own during a capture.
// ======================================================================

#include <sys/mman.h>
#include <unistd.h>
#include <cerrno>
#include <chrono>
#include <condition_variable>
#include <csetjmp>
#include <cstdio>
#include <memory>
#include <mutex>
#include <vector>

#include <jpeglib.h>
#include <libcamera/libcamera.h>

#include "Components/PiCamera/CameraFactory.hpp"

namespace PiSensor {

namespace {

//! libjpeg error manager that returns to the caller instead of exiting
struct JpegError {
    jpeg_error_mgr base;
    jmp_buf jump;
};

void jpegErrorExit(j_common_ptr cinfo) {
    JpegError* error = reinterpret_cast<JpegError*>(cinfo->err);
    longjmp(error->jump, 1);
}

void jpegNoMessage(j_common_ptr cinfo) {
    static_cast<void>(cinfo);
}

//! libjpeg destination that writes into a fixed buffer and records an overflow
struct JpegDestination {
    jpeg_destination_mgr base;
    JOCTET* buffer;
    size_t capacity;
    bool full;            //!< The destination was filled
    bool overflow;        //!< The scratch area was filled too
    JOCTET scratch[256];  //!< Receives the bytes beyond the destination
};

void jpegInitDestination(j_compress_ptr cinfo) {
    JpegDestination* dest = reinterpret_cast<JpegDestination*>(cinfo->dest);
    dest->base.next_output_byte = dest->buffer;
    dest->base.free_in_buffer = dest->capacity;
}

boolean jpegEmptyOutputBuffer(j_compress_ptr cinfo) {
    // libjpeg calls this when the buffer is full, also when the JPEG ends exactly there.
    // Later bytes go to a scratch area; one that receives a byte is the overflow.
    JpegDestination* dest = reinterpret_cast<JpegDestination*>(cinfo->dest);
    if (dest->full) {
        dest->overflow = true;
    }
    dest->full = true;
    dest->base.next_output_byte = dest->scratch;
    dest->base.free_in_buffer = sizeof(dest->scratch);
    return TRUE;
}

void jpegTermDestination(j_compress_ptr cinfo) {
    static_cast<void>(cinfo);
}

//! One mapped plane of a frame buffer
struct Plane {
    void* mapping;       //!< Start of the mapping
    size_t mappingSize;  //!< Size of the mapping
    const U8* data;      //!< First byte of the plane
    size_t size;         //!< Size of the plane
};

constexpr unsigned int PLANES = 3;         //!< Y, U, V
constexpr unsigned int MCU_LUMA_ROWS = 16;  //!< Luma rows per MCU row with 4:2:0 sampling
constexpr unsigned int NO_SETTLE = 0xFFFFFFFFU;

class LibcameraCamera final : public Camera {
  public:
    LibcameraCamera()
        : m_stream(nullptr),
          m_started(false),
          m_width(0),
          m_height(0),
          m_stride(0),
          m_frames(0),
          m_settle(NO_SETTLE),
          m_kept(nullptr),
          m_keptError(false) {}

    ~LibcameraCamera() override { this->close(); }

    Status detect(I32& code) override {
        this->close();
        this->m_manager = std::make_unique<libcamera::CameraManager>();
        const int ret = this->m_manager->start();
        if (ret != 0) {
            code = ret;
            this->m_manager.reset();
            return Status::ERROR;
        }
        if (this->m_manager->cameras().empty()) {
            return Status::NO_CAMERA;
        }
        return Status::OK;
    }

    Status open(I32& code) override {
        if (!this->m_manager) {
            code = -ENODEV;
            return Status::ERROR;
        }
        const auto cameras = this->m_manager->cameras();
        if (cameras.empty()) {
            // The camera detect listed is gone: an error of this step, NO_CAMERA belongs to detect
            code = -ENODEV;
            return Status::ERROR;
        }
        this->m_camera = cameras[0];
        const int ret = this->m_camera->acquire();
        if (ret != 0) {
            code = ret;
            this->m_camera.reset();
            return Status::ERROR;
        }
        return Status::OK;
    }

    Status configure(U32 width, U32 height, I32& code) override {
        if (!this->m_camera || ((width % MCU_LUMA_ROWS) != 0) || ((height % MCU_LUMA_ROWS) != 0)) {
            code = -EINVAL;
            return Status::ERROR;
        }
        this->m_config = this->m_camera->generateConfiguration({libcamera::StreamRole::Viewfinder});
        if (!this->m_config || this->m_config->empty()) {
            code = -EINVAL;
            return Status::ERROR;
        }
        libcamera::StreamConfiguration& stream = this->m_config->at(0);
        stream.pixelFormat = libcamera::formats::YUV420;
        stream.size = libcamera::Size(width, height);
        stream.colorSpace = libcamera::ColorSpace::Sycc;
        const libcamera::CameraConfiguration::Status valid = this->m_config->validate();
        const bool asAsked = (stream.pixelFormat == libcamera::formats::YUV420) && (stream.size.width == width) &&
                             (stream.size.height == height) && (stream.stride >= width);
        if ((valid == libcamera::CameraConfiguration::Invalid) || (!asAsked)) {
            code = -EINVAL;
            return Status::ERROR;
        }
        const int ret = this->m_camera->configure(this->m_config.get());
        if (ret != 0) {
            code = ret;
            return Status::ERROR;
        }
        this->m_stream = stream.stream();
        this->m_width = width;
        this->m_height = height;
        this->m_stride = stream.stride;
        return Status::OK;
    }

    Status start(I32& code) override {
        if (!this->m_camera || (this->m_stream == nullptr)) {
            code = -EINVAL;
            return Status::ERROR;
        }
        this->m_allocator = std::make_unique<libcamera::FrameBufferAllocator>(this->m_camera);
        int ret = this->m_allocator->allocate(this->m_stream);
        if (ret < 0) {
            code = ret;
            return Status::ERROR;
        }
        for (const std::unique_ptr<libcamera::FrameBuffer>& buffer : this->m_allocator->buffers(this->m_stream)) {
            std::unique_ptr<libcamera::Request> request = this->m_camera->createRequest();
            if (!request) {
                code = -ENOMEM;
                return Status::ERROR;
            }
            ret = request->addBuffer(this->m_stream, buffer.get());
            if (ret != 0) {
                code = ret;
                return Status::ERROR;
            }
            this->m_requests.push_back(std::move(request));
        }
        {
            std::lock_guard<std::mutex> lock(this->m_mutex);
            this->m_frames = 0;
            this->m_settle = NO_SETTLE;
            this->m_kept = nullptr;
            this->m_keptError = false;
        }
        this->m_camera->requestCompleted.connect(this, &LibcameraCamera::requestCompleted);
        ret = this->m_camera->start();
        if (ret != 0) {
            code = ret;
            this->m_camera->requestCompleted.disconnect(this, &LibcameraCamera::requestCompleted);
            return Status::ERROR;
        }
        this->m_started = true;
        for (const std::unique_ptr<libcamera::Request>& request : this->m_requests) {
            ret = this->m_camera->queueRequest(request.get());
            if (ret != 0) {
                code = ret;
                return Status::ERROR;
            }
        }
        return Status::OK;
    }

    Status waitFrame(U32 timeoutMs, U32 settleFrames, I32& code) override {
        if (!this->m_started) {
            code = -EINVAL;
            return Status::ERROR;
        }
        std::unique_lock<std::mutex> lock(this->m_mutex);
        this->m_settle = settleFrames;
        // steady_clock is monotonic
        const std::chrono::steady_clock::time_point limit =
            std::chrono::steady_clock::now() + std::chrono::milliseconds(timeoutMs);
        const bool arrived = this->m_condition.wait_until(lock, limit, [this] { return this->m_kept != nullptr; });
        if (!arrived) {
            // A frame that arrives from now on is discarded
            this->m_settle = NO_SETTLE;
            return Status::TIMEOUT;
        }
        if (this->m_keptError) {
            code = -EIO;
            return Status::ERROR;
        }
        return Status::OK;
    }

    Status encode(U32 quality, U8* dst, FwSizeType capacity, FwSizeType& size, I32& code) override {
        size = 0;
        libcamera::FrameBuffer* frame = nullptr;
        {
            std::lock_guard<std::mutex> lock(this->m_mutex);
            frame = this->m_keptError ? nullptr : this->m_kept;
        }
        if ((frame == nullptr) || (dst == nullptr) || (capacity == 0)) {
            code = -EINVAL;
            return Status::ERROR;
        }
        Plane planes[PLANES] = {};
        Status status = this->mapFrame(*frame, planes, code);
        if (status == Status::OK) {
            status = this->compress(planes, quality, dst, capacity, size, code);
        }
        unmapFrame(planes);
        return status;
    }

    void stop() override {
        if (this->m_camera && this->m_started) {
            // Returns after every outstanding request completed: no callback runs afterwards
            static_cast<void>(this->m_camera->stop());
            this->m_camera->requestCompleted.disconnect(this, &LibcameraCamera::requestCompleted);
        }
        this->m_started = false;
        {
            std::lock_guard<std::mutex> lock(this->m_mutex);
            this->m_kept = nullptr;
            this->m_keptError = false;
            this->m_settle = NO_SETTLE;
        }
        this->m_requests.clear();
        if (this->m_allocator && (this->m_stream != nullptr)) {
            static_cast<void>(this->m_allocator->free(this->m_stream));
        }
        this->m_allocator.reset();
    }

    void close() override {
        this->stop();
        this->m_stream = nullptr;
        this->m_config.reset();
        if (this->m_camera) {
            static_cast<void>(this->m_camera->release());
            this->m_camera.reset();
        }
        if (this->m_manager) {
            this->m_manager->stop();
            this->m_manager.reset();
        }
    }

  private:
    //! Runs on the camera library thread
    void requestCompleted(libcamera::Request* request) {
        if (request->status() == libcamera::Request::RequestCancelled) {
            return;
        }
        std::lock_guard<std::mutex> lock(this->m_mutex);
        if (this->m_kept != nullptr) {
            return;
        }
        libcamera::FrameBuffer* buffer = request->findBuffer(this->m_stream);
        if ((this->m_settle != NO_SETTLE) && (this->m_frames >= this->m_settle) && (buffer != nullptr)) {
            this->m_kept = buffer;
            this->m_keptError = !this->complete(*buffer);
            this->m_condition.notify_all();
            return;
        }
        if (this->m_frames < NO_SETTLE - 1) {
            this->m_frames++;
        }
        request->reuse(libcamera::Request::ReuseBuffers);
        static_cast<void>(this->m_camera->queueRequest(request));
    }

    //! A frame is complete when the camera reports success and every plane is filled
    bool complete(const libcamera::FrameBuffer& buffer) const {
        const libcamera::FrameMetadata& metadata = buffer.metadata();
        if (metadata.status != libcamera::FrameMetadata::FrameSuccess) {
            return false;
        }
        const size_t chromaStride = this->m_stride / 2;
        const size_t expected[PLANES] = {static_cast<size_t>(this->m_stride) * this->m_height,
                                         chromaStride * (this->m_height / 2), chromaStride * (this->m_height / 2)};
        const auto planes = metadata.planes();
        if (planes.size() != PLANES) {
            return false;
        }
        for (unsigned int i = 0; i < PLANES; i++) {
            if (planes[i].bytesused < expected[i]) {
                return false;
            }
        }
        return true;
    }

    Status mapFrame(const libcamera::FrameBuffer& frame, Plane planes[PLANES], I32& code) const {
        const auto& framePlanes = frame.planes();
        if (framePlanes.size() != PLANES) {
            code = -EINVAL;
            return Status::ERROR;
        }
        for (unsigned int i = 0; i < PLANES; i++) {
            const libcamera::FrameBuffer::Plane& plane = framePlanes[i];
            const size_t mappingSize = static_cast<size_t>(plane.offset) + plane.length;
            void* mapping = ::mmap(nullptr, mappingSize, PROT_READ, MAP_SHARED, plane.fd.get(), 0);
            if (mapping == MAP_FAILED) {
                code = -errno;
                return Status::ERROR;
            }
            planes[i].mapping = mapping;
            planes[i].mappingSize = mappingSize;
            planes[i].data = static_cast<const U8*>(mapping) + plane.offset;
            planes[i].size = plane.length;
        }
        return Status::OK;
    }

    static void unmapFrame(Plane planes[PLANES]) {
        for (unsigned int i = 0; i < PLANES; i++) {
            if (planes[i].mapping != nullptr) {
                static_cast<void>(::munmap(planes[i].mapping, planes[i].mappingSize));
                planes[i].mapping = nullptr;
            }
        }
    }

    Status compress(const Plane planes[PLANES], U32 quality, U8* dst, FwSizeType capacity, FwSizeType& size, I32& code)
        const {
        const size_t chromaStride = this->m_stride / 2;
        const unsigned int chromaHeight = this->m_height / 2;
        if ((planes[0].size < static_cast<size_t>(this->m_stride) * this->m_height) ||
            (planes[1].size < chromaStride * chromaHeight) || (planes[2].size < chromaStride * chromaHeight)) {
            code = -EINVAL;
            return Status::ERROR;
        }

        jpeg_compress_struct cinfo;
        JpegError error;
        JpegDestination dest;
        cinfo.err = jpeg_std_error(&error.base);
        error.base.error_exit = jpegErrorExit;
        error.base.output_message = jpegNoMessage;
        if (setjmp(error.jump) != 0) {
            code = error.base.msg_code;
            jpeg_destroy_compress(&cinfo);
            return Status::ERROR;
        }
        jpeg_create_compress(&cinfo);
        dest.base.init_destination = jpegInitDestination;
        dest.base.empty_output_buffer = jpegEmptyOutputBuffer;
        dest.base.term_destination = jpegTermDestination;
        dest.buffer = dst;
        dest.capacity = static_cast<size_t>(capacity);
        dest.full = false;
        dest.overflow = false;
        cinfo.dest = &dest.base;

        cinfo.image_width = this->m_width;
        cinfo.image_height = this->m_height;
        cinfo.input_components = static_cast<int>(PLANES);
        cinfo.in_color_space = JCS_YCbCr;
        jpeg_set_defaults(&cinfo);
        jpeg_set_colorspace(&cinfo, JCS_YCbCr);
        jpeg_set_quality(&cinfo, static_cast<int>(quality), TRUE);
        cinfo.raw_data_in = TRUE;
        cinfo.comp_info[0].h_samp_factor = 2;
        cinfo.comp_info[0].v_samp_factor = 2;
        cinfo.comp_info[1].h_samp_factor = 1;
        cinfo.comp_info[1].v_samp_factor = 1;
        cinfo.comp_info[2].h_samp_factor = 1;
        cinfo.comp_info[2].v_samp_factor = 1;
        jpeg_start_compress(&cinfo, TRUE);

        JSAMPROW yRows[MCU_LUMA_ROWS];
        JSAMPROW uRows[MCU_LUMA_ROWS / 2];
        JSAMPROW vRows[MCU_LUMA_ROWS / 2];
        JSAMPARRAY rows[PLANES] = {yRows, uRows, vRows};
        // The height is a multiple of MCU_LUMA_ROWS (checked in configure)
        for (unsigned int row = 0; row < this->m_height; row += MCU_LUMA_ROWS) {
            for (unsigned int i = 0; i < MCU_LUMA_ROWS; i++) {
                yRows[i] = const_cast<JSAMPROW>(planes[0].data + static_cast<size_t>(row + i) * this->m_stride);
            }
            for (unsigned int i = 0; i < MCU_LUMA_ROWS / 2; i++) {
                const size_t offset = static_cast<size_t>(row / 2 + i) * chromaStride;
                uRows[i] = const_cast<JSAMPROW>(planes[1].data + offset);
                vRows[i] = const_cast<JSAMPROW>(planes[2].data + offset);
            }
            static_cast<void>(jpeg_write_raw_data(&cinfo, rows, MCU_LUMA_ROWS));
        }
        jpeg_finish_compress(&cinfo);
        // Once full, free_in_buffer counts the scratch area
        const bool beyond = dest.overflow || (dest.full && (dest.base.free_in_buffer != sizeof(dest.scratch)));
        const size_t written = dest.full ? dest.capacity : (dest.capacity - dest.base.free_in_buffer);
        jpeg_destroy_compress(&cinfo);
        if (beyond) {
            return Status::TOO_LARGE;
        }
        size = static_cast<FwSizeType>(written);
        return Status::OK;
    }

    std::unique_ptr<libcamera::CameraManager> m_manager;
    std::shared_ptr<libcamera::Camera> m_camera;
    std::unique_ptr<libcamera::CameraConfiguration> m_config;
    std::unique_ptr<libcamera::FrameBufferAllocator> m_allocator;
    std::vector<std::unique_ptr<libcamera::Request>> m_requests;
    libcamera::Stream* m_stream;
    bool m_started;
    unsigned int m_width;
    unsigned int m_height;
    unsigned int m_stride;

    std::mutex m_mutex;                   //!< Guards the members below
    std::condition_variable m_condition;  //!< Signals a kept frame
    unsigned int m_frames;                //!< Frames discarded since start
    unsigned int m_settle;                //!< Frames to discard before one is kept; NO_SETTLE keeps none
    libcamera::FrameBuffer* m_kept;       //!< The kept frame
    bool m_keptError;                     //!< The kept frame is in error or incomplete
};

}  // namespace

Camera& getCamera() {
    static LibcameraCamera camera;
    return camera;
}

}  // namespace PiSensor
