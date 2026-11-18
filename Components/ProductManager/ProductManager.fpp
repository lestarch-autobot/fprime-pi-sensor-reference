module PiSensor {

  @ Request to acquire one picture
  port CaptureRequest(
    context: U32 @< Returned with the picture
  )

  @ Result of one picture acquisition
  port PictureDone(
    context: U32 @< Context of the request
    status: Fw.Success @< SUCCESS when the buffer holds one picture
    captureTime: Fw.TimeValue @< Time the picture was acquired, time base of the system time source
    ref picture: Fw.Buffer @< The picture, to be returned to the camera
  )

  @ Temperature sample or record
  struct TemperatureSample {
    valid: bool @< Validity mark
    sampleTime: Fw.TimeValue @< Time of the sample, time base of the system time source
    temperature: F32 @< degC
  }

  @ Attitude sample or record
  struct AttitudeSample {
    valid: bool @< Validity mark
    sampleTime: Fw.TimeValue @< Time of the sample, time base of the system time source
    roll: F32 @< deg, about the sensor x axis, from gravity
    pitch: F32 @< deg, about the sensor y axis, from gravity
    gyroRate: [3] F32 @< deg/s about the sensor x, y, z axes; no yaw angle is given
  }

  @ Location sample or record
  struct LocationSample {
    valid: bool @< Validity mark
    sampleTime: Fw.TimeValue @< Time of the sample, time base of the system time source
    latitude: F64 @< deg, WGS 84, north positive
    longitude: F64 @< deg, WGS 84, east positive
    altitude: F32 @< m above mean sea level, as the receiver reports
  }

  @ Latest sample of every metric
  struct SampleSet {
    temperature: TemperatureSample
    attitude: AttitudeSample
    location: LocationSample
  }

  @ Request for the latest sample of every metric
  port SamplesGet(
    ref samples: SampleSet @< Filled by the callee
  )

  @ Product manager: capture, downlink, delete and list commands; builds the data product
  active component ProductManager {

    # ----------------------------------------------------------------------
    # Types and constants
    # ----------------------------------------------------------------------

    @ Run ticks allowed for the camera to deliver the picture
    constant PICTURE_TIMEOUT_TICKS = 20

    @ Run ticks allowed for the storage to store the product
    constant WRITTEN_TIMEOUT_TICKS = 5

    @ Run ticks during which the file of a failed capture is removed if it appears
    constant DISCARD_RECHECK_TICKS = 5

    @ ProductStored events emitted per run tick
    constant LIST_EVENTS_PER_TICK = 4

    @ Directory entries read by a listing per run tick
    constant LIST_ENTRIES_PER_TICK = 64

    @ Directory entries examined by one start-up scan
    constant SCAN_MAX_ENTRIES = 4096

    @ Length of a product name
    constant PRODUCT_NAME_SIZE = 40

    @ Command refused because of the activity in progress
    enum RejectReason : U8 {
      CAPTURE_IN_PROGRESS
      DOWNLINK_IN_PROGRESS
      PRODUCT_IN_DOWNLINK
      LISTING_IN_PROGRESS
    }

    @ Cause of a failed capture
    enum CaptureFailure : U8 {
      CAMERA_FAILED
      PICTURE_EMPTY
      PICTURE_TIMEOUT
    }

    @ Cause of a storage failure
    enum StorageFailure : U8 {
      NO_BUFFER
      NAME_IN_USE
      WRITTEN_TIMEOUT
    }

    @ Capture activity
    enum CaptureState : U8 {
      IDLE
      WAIT_PICTURE
      WAIT_WRITTEN
    }

    @ Downlink or listing activity
    enum Activity : U8 {
      IDLE
      ACTIVE
    }

    @ File system operation that failed
    enum FileOp : U8 {
      SCAN_OPEN
      SCAN_READ
      SCAN_REMOVE
      DISCARD_REMOVE
      DELETE_REMOVE
      LIST_OPEN
      LIST_READ
      FILE_READ
    }

    @ Why a file was removed without a DELETE command
    enum DiscardReason : U8 {
      PARTIAL_AT_STARTUP
      FAILED_CAPTURE
      LATE_FILE
    }

    # ----------------------------------------------------------------------
    # General ports
    # ----------------------------------------------------------------------

    @ Picture request to the camera
    output port captureOut: CaptureRequest

    @ Picture or failure from the camera
    async input port imageIn: PictureDone hook

    @ Picture buffer back to the camera
    output port imageReturnOut: Fw.BufferSend

    @ Latest samples from the sensor monitor
    output port samplesGetOut: SamplesGet

    @ Named product to the file transfer
    output port sendFileOut: Svc.SendFileRequest

    @ File transfer ended
    async input port fileDoneIn: Svc.SendFileComplete hook

    @ 1 Hz tick: time-outs, stored check of the capture, listing
    async input port run: Svc.Sched drop

    # ----------------------------------------------------------------------
    # Data product
    # ----------------------------------------------------------------------

    product get port productGetOut

    product send port productSendOut

    @ Time the picture was acquired
    product record CaptureTime: Fw.TimeValue id 0

    @ Temperature at capture
    product record Temperature: TemperatureSample id 1

    @ Attitude at capture
    product record Attitude: AttitudeSample id 2

    @ Location at capture
    product record Location: LocationSample id 3

    @ The picture, JPEG bytes as delivered
    product record Picture: U8 array id 4

    @ One capture
    product container Capture id 0 default priority 10

    # ----------------------------------------------------------------------
    # Commands
    # ----------------------------------------------------------------------

    @ Capture one picture and store it with the metrics as one product
    async command CAPTURE() hook

    @ Send the named product to the ground by CFDP
    async command DOWNLINK(
      name: string size PRODUCT_NAME_SIZE @< Product name
    ) hook

    @ Remove the named product
    async command DELETE(
      name: string size PRODUCT_NAME_SIZE @< Product name
    ) hook

    @ Report the stored products
    async command LIST_PRODUCTS() hook

    # ----------------------------------------------------------------------
    # Events
    # ----------------------------------------------------------------------

    @ A capture ended with its product stored
    event ProductWritten(
      name: string size PRODUCT_NAME_SIZE
      $size: FwSizeType
    ) severity activity high format "Product {} written, {} bytes"

    @ The camera gave no usable picture
    event CaptureFailed(
      reason: CaptureFailure
    ) severity warning high format "Capture failed: {}"

    @ The product could not be stored
    event StorageFailed(
      reason: StorageFailure
    ) severity warning high format "Product storage failed: {}"

    @ A command was refused because of the activity in progress
    event CommandRejected(
      reason: RejectReason
    ) severity warning low format "Command rejected: {}"

    @ The file transfer accepted the product
    event DownlinkStarted(
      name: string size PRODUCT_NAME_SIZE
    ) severity activity high format "Downlink of {} started"

    @ The file transfer delivered the product
    event DownlinkComplete(
      name: string size PRODUCT_NAME_SIZE
    ) severity activity high format "Downlink of {} complete"

    @ The file transfer ended without delivering the product
    event DownlinkStalled(
      name: string size PRODUCT_NAME_SIZE
    ) severity warning high format "Downlink of {} ended without delivery"

    @ The file transfer refused the request
    event DownlinkRefused(
      name: string size PRODUCT_NAME_SIZE
      status: Svc.SendFileStatus
    ) severity warning low format "Downlink of {} refused: {}"

    @ The name is not that of a stored product
    event ProductNotFound(
      name: string size PRODUCT_NAME_SIZE
    ) severity warning low format "No stored product {}"

    @ The named product was removed
    event ProductDeleted(
      name: string size PRODUCT_NAME_SIZE
    ) severity activity high format "Product {} deleted"

    @ One stored product of a listing
    event ProductStored(
      name: string size PRODUCT_NAME_SIZE
      $size: FwSizeType
    ) severity activity low format "Product {}, {} bytes"

    @ A listing ended
    event ProductsListed(
      count: U32
    ) severity activity high format "{} products stored"

    @ A file was removed without a DELETE command
    event ProductDiscarded(
      name: string size PRODUCT_NAME_SIZE
      reason: DiscardReason
    ) severity warning low format "File {} removed: {}"

    @ The file system reported an error
    event FileSystemError(
      op: FileOp
      name: string size PRODUCT_NAME_SIZE @< File concerned, empty for a directory operation
      status: I32 @< Os::FileSystem or Os::Directory status
    ) severity warning high format "File system error in {} on {}: {}"

    @ The start-up scan ended
    event ScanComplete(
      stored: U32 @< Stored products found
      removed: U32 @< Partial products removed
      truncated: bool @< The scan stopped at SCAN_MAX_ENTRIES
    ) severity activity high format "Start-up scan: {} products stored, {} files removed, truncated {}"

    # ----------------------------------------------------------------------
    # Telemetry
    # ----------------------------------------------------------------------

    @ Capture activity
    telemetry CaptureActivity: CaptureState update on change

    @ Downlink activity
    telemetry DownlinkActivity: Activity update on change

    @ Listing activity
    telemetry ListingActivity: Activity update on change

    # ----------------------------------------------------------------------
    # Special ports
    # ----------------------------------------------------------------------

    command recv port cmdIn

    command reg port cmdRegOut

    command resp port cmdResponseOut

    event port eventOut

    text event port textEventOut

    telemetry port tlmOut

    time get port timeGetOut

  }

}
