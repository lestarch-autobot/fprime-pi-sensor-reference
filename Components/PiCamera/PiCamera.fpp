module PiSensor {

  @ Pi Camera manager: acquires one JPEG per request
  active component PiCamera {

    @ Step of a capture at which a failure is found
    enum CaptureStep : U8 {
      RECEIVE = 0 @< Receipt of the request: an earlier request has no reply
      RETURN = 1 @< Receipt of the request: the last picture is not returned
      DETECT = 2 @< Camera detection
      OPEN = 3 @< Camera acquisition for exclusive use
      CONFIGURE = 4 @< Camera configuration
      START = 5 @< Camera start
      FRAME = 6 @< Frame completion
      ALLOCATE = 7 @< Picture buffer allocation
      ENCODE = 8 @< JPEG encoding
      TICKS = 9 @< Tick count of the capture timeout
    }

    @ Picture width in pixels
    constant PICTURE_WIDTH = 640

    @ Picture height in pixels
    constant PICTURE_HEIGHT = 480

    @ Size in bytes of the picture buffer requested per capture
    constant PICTURE_BUFFER_SIZE = 262144

    @ Ticks of the run port from receipt of a request to its reply
    constant CAPTURE_TIMEOUT_TICKS = 10

    @ Frames discarded before the delivered frame, for exposure to settle
    constant SETTLE_FRAMES = 10

    @ Capture request, decided in the caller's thread
    guarded input port captureIn: CaptureRequest

    @ Reply to each capture request; connect to an async input
    output port imageOut: CaptureReply

    @ Picture buffer returned by the requester
    guarded input port imageReturnIn: Fw.BufferSend

    @ Tick that counts the capture timeout, 1 Hz
    guarded input port run: Svc.Sched

    @ Picture buffer allocation
    output port allocate: Fw.BufferGet

    @ Picture buffer release
    output port deallocate: Fw.BufferSend

    @ Health ping
    async input port pingIn: Svc.Ping drop

    @ Health ping reply
    output port pingOut: Svc.Ping

    @ Detect the camera once at start
    internal port detect drop

    @ Open, configure and start the camera for a capture
    internal port acquire(
      capture: U32 @< Number of the capture
    ) drop

    @ Close the camera of a capture that timed out
    internal port abort(
      capture: U32 @< Number of the capture
    ) drop

    @ The camera library reports the frame of a capture, from its own thread
    internal port frameDone(
      capture: U32 @< Number of the capture the frame belongs to
      ok: bool @< The frame is complete
      acquired: Fw.Time @< System time read when the frame arrived
    ) drop

    event port eventOut
    text event port textEventOut
    telemetry port tlmOut
    time get port timeGetOut

    @ Acquisition of a picture begins
    event CaptureStarted(
      context: U32 @< Context of the request
    ) severity activity low format "Capture {} started"

    @ A capture request failed
    event CaptureFailed(
      context: U32 @< Context of the request
      reason: CaptureStatus @< Failure reason
      step: CaptureStep @< Step at which the failure was found
      code: I32 @< Return code of the camera or JPEG library at that step, else 0
    ) severity warning low format "Capture {} failed: {} at {} code {}"

    @ A returned buffer was not released: it is not the delivered picture
    event ReturnRejected(
      bytes: FwSizeType @< Size in bytes of the returned buffer
    ) severity warning low format "Returned buffer of {} bytes rejected"

    @ A camera is detected at start
    event CameraFound(
      camera: string size 80 @< Identification the camera library gives
    ) severity activity low format "Camera found: {}"

    @ No camera is detected at start
    event CameraNotFound severity warning low format "No camera found"

    @ Count of success replies since start
    telemetry CapturesCompleted: U32

    @ Count of failure replies since start
    telemetry CapturesFailed: U32

    @ Size in bytes of the last delivered JPEG
    telemetry LastPictureSize: U32

    @ A camera was detected at the last detection
    telemetry CameraPresent: bool

    @ A delivered picture is not yet returned
    telemetry PictureOutstanding: bool

  }
}
