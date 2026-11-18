module PiSensor {

  @ Outcome of one picture acquisition
  enum PictureStatus : U8 {
    OK @< The buffer holds one picture
    FAILED @< No picture was acquired
  }

  @ Request to acquire one picture
  port CaptureRequest(
    context: U32 @< Returned with the picture
  )

  @ Result of one picture acquisition
  port PictureDone(
    context: U32 @< Context of the request
    status: PictureStatus @< Outcome of the acquisition
    captureTime: Fw.TimeValue @< Time the picture was acquired
    ref picture: Fw.Buffer @< The picture, to be returned to the camera
  )

  @ Temperature sample or record
  struct TemperatureSample {
    valid: bool
    sampleTime: Fw.TimeValue
    temperature: F32 @< degC
  }

  @ Attitude sample or record
  struct AttitudeSample {
    valid: bool
    sampleTime: Fw.TimeValue
    roll: F32 @< deg
    pitch: F32 @< deg
    gyroRate: [3] F32 @< deg/s, x y z
  }

  @ Location sample or record
  struct LocationSample {
    valid: bool
    sampleTime: Fw.TimeValue
    latitude: F64 @< deg
    longitude: F64 @< deg
    altitude: F32 @< m
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

    @ Run ticks allowed for the storage to report the product written
    constant WRITTEN_TIMEOUT_TICKS = 5

    @ ProductStored events emitted per run tick
    constant LIST_EVENTS_PER_TICK = 4

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

    @ File system operation that failed
    enum FileOp : U8 {
      SCAN_OPEN
      SCAN_REMOVE
      CAPTURE_REMOVE
      DELETE_REMOVE
      LIST_OPEN
      LIST_READ
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

    @ Product file written by the storage
    async input port dpWrittenIn: Svc.DpWritten

    @ Named product to the file transfer
    output port sendFileOut: Svc.SendFileRequest

    @ File transfer ended
    async input port fileDoneIn: Svc.SendFileComplete

    @ 1 Hz tick: time-outs, listing, start-up scan
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

    @ A partial product was removed
    event PartialRemoved(
      name: string size PRODUCT_NAME_SIZE
    ) severity activity low format "Partial product {} removed"

    @ The file system reported an error
    event FileSystemError(
      op: FileOp
      status: I32
    ) severity warning high format "File system error in {}: {}"

    # ----------------------------------------------------------------------
    # Special ports
    # ----------------------------------------------------------------------

    command recv port cmdIn

    command reg port cmdRegOut

    command resp port cmdResponseOut

    event port eventOut

    text event port textEventOut

    time get port timeGetOut

  }

}
