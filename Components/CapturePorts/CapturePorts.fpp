module PiSensor {

  @ Outcome of one capture request
  enum CaptureStatus : U8 {
    OK = 0 @< A picture is delivered
    NO_CAMERA = 1 @< No camera is detected
    CAMERA_ERROR = 2 @< The camera, its library or the JPEG encoding fails or yields no complete picture
    TIMEOUT = 3 @< No picture was ready within CAPTURE_TIMEOUT_TICKS ticks of the request
    NO_BUFFER = 4 @< No picture buffer is available
    TOO_LARGE = 5 @< The JPEG does not fit the picture buffer
    BUSY = 6 @< An earlier request has no reply yet
    PICTURE_OUTSTANDING = 7 @< The last delivered picture is not yet returned
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
    ref picture: Fw.Buffer @< The JPEG when status is OK, its size set to the JPEG length in bytes; else an invalid buffer
  )

}
