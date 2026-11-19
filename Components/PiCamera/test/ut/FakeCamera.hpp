// ======================================================================
// \title  FakeCamera.hpp
// \brief  Camera interface substitute for the PiCamera unit tests
// ======================================================================

#ifndef PiSensor_FakeCamera_HPP
#define PiSensor_FakeCamera_HPP

#include <cstring>
#include <functional>

#include "Components/PiCamera/Camera.hpp"

namespace PiSensor {

class FakeCamera final : public Camera {
  public:
    //! The calls of the interface, in the order of a capture
    enum Call { DETECT, OPEN, CONFIGURE, START, WAIT_FRAME, ENCODE, STOP, CLOSE, NUM_CALLS };

    static constexpr U32 MAX_LOG = 32;

    FakeCamera() { this->reset(); }

    //! Every call succeeds, the JPEG has 1000 bytes, the log is empty
    void reset() {
        for (U32 i = 0; i < NUM_CALLS; i++) {
            this->status[i] = Status::OK;
            this->code[i] = 0;
            this->count[i] = 0;
        }
        this->jpegSize = 1000;
        this->fill = 0xA5;
        this->logSize = 0;
        this->timeoutMs = 0;
        this->settleFrames = 0;
        this->width = 0;
        this->height = 0;
        this->quality = 0;
        this->capacity = 0;
        this->onDetect = nullptr;
        this->onFrame = nullptr;
    }

    //! Forget the calls, keep the script
    void clearLog() {
        this->logSize = 0;
        for (U32 i = 0; i < NUM_CALLS; i++) {
            this->count[i] = 0;
        }
    }

    Status detect(I32& c) override {
        if (this->onDetect) {
            this->onDetect();
        }
        return this->call(DETECT, c);
    }
    Status open(I32& c) override { return this->call(OPEN, c); }
    Status configure(U32 w, U32 h, I32& c) override {
        this->width = w;
        this->height = h;
        return this->call(CONFIGURE, c);
    }
    Status start(I32& c) override { return this->call(START, c); }
    Status waitFrame(U32 timeout, U32 settle, I32& c) override {
        this->timeoutMs = timeout;
        this->settleFrames = settle;
        if (this->onFrame) {
            this->onFrame();
        }
        return this->call(WAIT_FRAME, c);
    }
    Status encode(U32 q, U8* dst, FwSizeType cap, FwSizeType& size, I32& c) override {
        this->quality = q;
        this->capacity = cap;
        const Status result = this->call(ENCODE, c);
        if (result != Status::OK) {
            return result;
        }
        if (this->jpegSize > cap) {
            return Status::TOO_LARGE;
        }
        (void)memset(dst, this->fill, static_cast<size_t>(this->jpegSize));
        size = this->jpegSize;
        return Status::OK;
    }
    void stop() override {
        I32 unused = 0;
        static_cast<void>(this->call(STOP, unused));
    }
    void close() override {
        I32 unused = 0;
        static_cast<void>(this->call(CLOSE, unused));
    }

    Status status[NUM_CALLS];        //!< Result of each call
    I32 code[NUM_CALLS];             //!< Code each call reports
    U32 count[NUM_CALLS];            //!< Times each call was made
    FwSizeType jpegSize;             //!< Size of the JPEG encode writes
    U8 fill;                         //!< Byte the JPEG is filled with
    Call log[MAX_LOG];               //!< The calls in order
    U32 logSize;                     //!< Entries in the log
    U32 timeoutMs;                   //!< Limit waitFrame was asked for
    U32 settleFrames;                //!< Frames waitFrame was asked to discard
    U32 width;                       //!< Width configure was asked for
    U32 height;                      //!< Height configure was asked for
    U32 quality;                     //!< Quality encode was asked for
    FwSizeType capacity;             //!< Destination size encode was given
    std::function<void()> onDetect;  //!< Runs at the start of detect
    std::function<void()> onFrame;   //!< Runs when the frame is handed over

  private:
    Status call(Call which, I32& c) {
        this->count[which]++;
        if (this->logSize < MAX_LOG) {
            this->log[this->logSize] = which;
            this->logSize++;
        }
        c = this->code[which];
        return this->status[which];
    }
};

}  // namespace PiSensor

#endif
