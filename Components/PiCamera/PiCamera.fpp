module PiSensor {

  @ Pi Camera: on a capture command acquires one JPEG, reads the latest
  @ sensor readings from the telemetry store and writes one product container
  active component PiCamera {

    # ----------------------------------------------------------------------
    # Types and constants
    # ----------------------------------------------------------------------

    @ Why a capture command failed
    enum FailReason : U8 {
      BUSY = 0 @< An earlier capture has not ended
      NO_CAMERA = 1 @< The camera library lists no camera
      CAMERA_ERROR = 2 @< A camera or JPEG library call failed or the frame is in error
      TIMEOUT = 3 @< No frame arrived within FRAME_TIMEOUT_MS
      TOO_LARGE = 4 @< The JPEG exceeds PICTURE_MAX_SIZE
      SENSOR_NO_DATA = 5 @< The telemetry store holds no usable reading
      SENSOR_STALE = 6 @< A reading is older or newer than METRIC_MAX_AGE_MS
      METRIC_INVALID = 7 @< A reading holds a value outside its range
      NO_CONTAINER = 8 @< No product container buffer was obtained
    }

    @ Where a capture command failed
    enum FailStep : U8 {
      RECEIVE = 0 @< Receipt of the command
      DETECT = 1 @< Listing the cameras
      OPEN = 2 @< Opening the camera
      CONFIGURE = 3 @< Configuring the camera
      START = 4 @< Starting the camera
      FRAME = 5 @< Waiting for or reading the frame
      TEMPERATURE = 6 @< Reading the temperature
      ATTITUDE = 7 @< Reading the acceleration
      LOCATION = 8 @< Reading latitude and longitude
      ENCODE = 9 @< Encoding the JPEG
      CONTAINER = 10 @< Getting the container buffer
    }

    @ Metrics stored with a picture
    struct CaptureMetrics {
      @ Time the frame was acquired
      captureTime: Fw.TimeValue
      @ Latitude in degrees, north positive
      latitude: F64
      @ Longitude in degrees, east positive
      longitude: F64
      @ Sample time of latitude and longitude
      locationTime: Fw.TimeValue
      @ Roll in degrees
      roll: F32
      @ Pitch in degrees
      pitch: F32
      @ Sample time of the acceleration behind roll and pitch
      attitudeTime: Fw.TimeValue
      @ Temperature in degrees Celsius
      temperature: F32
      @ Sample time of the temperature
      temperatureTime: Fw.TimeValue
    }

    @ Picture width in pixels
    constant PICTURE_WIDTH = 640

    @ Picture height in pixels
    constant PICTURE_HEIGHT = 480

    @ Largest JPEG stored, in bytes
    constant PICTURE_MAX_SIZE = 262144

    @ Longest wait for the frame, in milliseconds
    constant FRAME_TIMEOUT_MS = 10000

    @ Longest time from receipt of a capture command to its response, in milliseconds
    constant CAPTURE_MAX_MS = 15000

    @ Frames discarded while exposure settles
    constant SETTLE_FRAMES = 10

    @ libjpeg quality setting, 1 to 100
    constant JPEG_QUALITY = 90

    @ Largest difference between a sample time and the capture time, in milliseconds
    constant METRIC_MAX_AGE_MS = 2000

    # ----------------------------------------------------------------------
    # Ports
    # ----------------------------------------------------------------------

    @ Reads the latest value and time of a telemetry channel
    output port tlmGetOut: Fw.TlmGet

    @ Health ping
    async input port pingIn: Svc.Ping drop

    @ Health ping reply
    output port pingOut: Svc.Ping

    @ Work of one capture, on the component thread
    internal port acquire(
      opCode: FwOpcodeType @< Opcode of the command the capture answers
      cmdSeq: U32 @< Sequence number of that command
    )

    product get port productGetOut
    product send port productSendOut
    command recv port cmdIn
    command reg port cmdRegOut
    command resp port cmdResponseOut
    event port eventOut
    text event port textEventOut
    telemetry port tlmOut
    time get port timeGetOut

    # ----------------------------------------------------------------------
    # Commands
    # ----------------------------------------------------------------------

    @ Acquire one picture and store it with the latest metrics as one data product
    guarded command CAPTURE

    # ----------------------------------------------------------------------
    # Events
    # ----------------------------------------------------------------------

    @ A capture command is accepted; acquisition begins
    event CaptureStarted severity activity low format "Capture started"

    @ The container of a capture was sent
    event CaptureCompleted(
      bytes: U32 @< Size of the JPEG in bytes
    ) severity activity high format "Capture stored a picture of {} bytes"

    @ A capture command failed
    event CaptureFailed(
      reason: FailReason @< Why the capture failed
      step: FailStep @< Step that failed
      code: I32 @< Return code of the failing library call; sample age in ms for SENSOR_STALE, limited to the I32 range; else 0
    ) severity warning high format "Capture failed: {} at {} code {}"

    # ----------------------------------------------------------------------
    # Telemetry
    # ----------------------------------------------------------------------

    @ Captures that stored a product since start
    telemetry CapturesCompleted: U32

    @ Capture commands that failed since start
    telemetry CapturesFailed: U32

    @ Size in bytes of the last stored JPEG
    telemetry LastPictureSize: U32

    # ----------------------------------------------------------------------
    # Data products
    # ----------------------------------------------------------------------

    @ Metrics of one capture
    product record Metrics: CaptureMetrics

    @ JPEG picture of one capture
    product record Picture: U8 array

    @ One capture: metrics and picture
    product container Capture default priority 10
  }
}
