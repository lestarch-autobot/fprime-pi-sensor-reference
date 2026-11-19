// ======================================================================
// \title  NoCamera.cpp
// \brief  Camera interface that detects no camera (PICAMERA_NO_CAMERA)
// ======================================================================

#include "Components/PiCamera/CameraFactory.hpp"

namespace PiSensor {

namespace {

class NoCamera final : public Camera {
  public:
    Status detect(I32& code) override {
        code = 0;
        return Status::NO_CAMERA;
    }
    Status open(I32& code) override { return this->detect(code); }
    Status configure(U32 width, U32 height, I32& code) override {
        static_cast<void>(width);
        static_cast<void>(height);
        return this->detect(code);
    }
    Status start(I32& code) override { return this->detect(code); }
    Status waitFrame(U32 timeoutMs, U32 settleFrames, I32& code) override {
        static_cast<void>(timeoutMs);
        static_cast<void>(settleFrames);
        return this->detect(code);
    }
    Status encode(U32 quality, U8* dst, FwSizeType capacity, FwSizeType& size, I32& code) override {
        static_cast<void>(quality);
        static_cast<void>(dst);
        static_cast<void>(capacity);
        size = 0;
        return this->detect(code);
    }
    void stop() override {}
    void close() override {}
};

}  // namespace

Camera& getCamera() {
    static NoCamera camera;
    return camera;
}

}  // namespace PiSensor
