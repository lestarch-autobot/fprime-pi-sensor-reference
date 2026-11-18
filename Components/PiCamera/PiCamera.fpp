module PiSensor {

  @ Outcome of one capture request
  enum CaptureStatus : U8 {
    OK = 0 @< A picture is delivered
    NO_CAMERA = 1 @< No camera is detected
    CAMERA_ERROR = 2 @< The camera, its library or the JPEG encoding fails or yields no complete picture
    TIMEOUT = 3 @< No picture was ready within CAPTURE_TIMEOUT_TICKS ticks of the request
    NO_BUFFER = 4 @< No picture buffer is available, or the last delivered picture is not yet returned
    TOO_LARGE = 5 @< The JPEG does not fit the picture buffer
    BUSY = 6 @< An earlier request has no reply yet
  }

  @ Request to acquire one picture
  port CaptureRequest(
    context: U32 @< Value echoed in the reply
  )

  @ Reply to one capture request
  port CaptureReply(
    context: U32 @< Context of the request
    status: CaptureStatus @< Outcome
    ref acquired: Fw.Time @< Time the frame arrived, valid when status is OK
    ref picture: Fw.Buffer @< The JPEG when status is OK, else an invalid buffer
  )

  @ Pi Camera manager: acquires one JPEG per request
  active component PiCamera {

    # ----------------------------------------------------------------------
    # Constants
    # ----------------------------------------------------------------------

    @ Picture width in pixels
    constant PICTURE_WIDTH = 640

    @ Picture height in pixels
    constant PICTURE_HEIGHT = 480

    @ Size in bytes of the picture buffer requested per capture
    constant PICTURE_BUFFER_SIZE = 262144

    @ Ticks of the run port from receipt of a request to its reply
    constant CAPTURE_TIMEOUT_TICKS = 10

    @ Ticks of the run port after which a frame no longer starts JPEG encoding
    constant FRAME_DEADLINE_TICKS = 8

    @ Frames discarded before the delivered frame, for exposure to settle
    constant SETTLE_FRAMES = 10

    # ----------------------------------------------------------------------
    # General ports
    # ----------------------------------------------------------------------

    @ Capture request; a request that finds the queue full gets a BUSY reply
    async input port captureIn: CaptureRequest hook

    @ Reply to each capture request
    output port imageOut: CaptureReply

    @ Picture buffer returned by the requester
    async input port imageReturnIn: Fw.BufferSend hook

    @ Tick that counts the capture timeout
    async input port run: Svc.Sched drop

    @ Picture buffer allocation
    output port allocate: Fw.BufferGet

    @ Picture buffer release
    output port deallocate: Fw.BufferSend

    # ----------------------------------------------------------------------
    # Internal ports
    # ----------------------------------------------------------------------

    @ The camera library reports the frame of a capture, from its own thread
    internal port frameDone(
      capture: U32 @< Number of the capture the frame belongs to
      ok: bool @< The frame is complete
      acquired: Fw.Time @< System time read when the frame arrived
    ) drop

    # ----------------------------------------------------------------------
    # Special ports
    # ----------------------------------------------------------------------

    event port eventOut

    text event port textEventOut

    telemetry port tlmOut

    time get port timeGetOut

    # ----------------------------------------------------------------------
    # Events
    # ----------------------------------------------------------------------

    @ Acquisition of a picture begins
    event CaptureStarted(
      context: U32 @< Context of the request
    ) severity activity low id 0 format "Capture {} started"

    @ A capture request failed
    event CaptureFailed(
      context: U32 @< Context of the request
      reason: CaptureStatus @< Failure reason
    ) severity warning low id 1 format "Capture {} failed: {}"

    @ A returned buffer was not released: not delivered by this component, or already released
    event ReturnRejected(
      bytes: FwSizeType @< Size in bytes of the returned buffer
    ) severity warning low id 2 format "Returned buffer of {} bytes rejected"

    # ----------------------------------------------------------------------
    # Telemetry
    # ----------------------------------------------------------------------

    @ Count of success replies since start
    telemetry CapturesCompleted: U32 id 0

    @ Count of failure replies since start
    telemetry CapturesFailed: U32 id 1

    @ Size in bytes of the last delivered JPEG
    telemetry LastPictureSize: U32 id 2

  }

}
