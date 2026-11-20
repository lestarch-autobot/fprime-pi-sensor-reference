# Telemetry packets of the PiSensor deployment (Svc.TlmPacketizer, see
# PiSensor/project/config/CdhCoreTlmConfig.fpp). The group sets how often a packet may be sent
# (PiSensor/project/config/TlmPacketizerCfg.fpp); a packet is sent only when one of its
# channels was written since it was last sent. The sizes and rates are budgeted in
# docs/link-budget.md.
telemetry packets PiSensorPackets {

  # Group 0, every 1 Hz cycle. One packet per sensor, so that a sensor that stops producing
  # readings stops being downlinked instead of riding along with the others.
  packet Bmp id 1 group 0 {
    Bmp280.bmpManager.Reading
  }

  packet Imu id 2 group 0 {
    MpuImu.imuManager.Reading
  }

  packet Gps id 3 group 0 {
    NmeaGps.gpsManager.Reading
  }

  # Group 1, at most once every 5 s: radio link, command and product counters
  packet Link id 4 group 1 {
    Rfm69.rfm69Manager.PacketsTransmitted
    Rfm69.rfm69Manager.PacketsReceived
    Rfm69.rfm69Manager.RxCrcErrors
    Rfm69.rfm69Manager.LastRssi
    Rfm69.rfm69Manager.RadioState
    CdhCore.cmdDisp.CommandsDispatched
    CdhCore.cmdDisp.CommandErrors
    CdhCore.cmdDisp.CommandsDropped
    ComCcsds.comQueue.comQueueDepth
    ComCcsds.comQueue.buffQueueDepth
    piCamera.CapturesCompleted
    piCamera.CapturesFailed
    piCamera.LastPictureSize
    DataProducts.dpCat.CatalogDps
    DataProducts.dpCat.DpsSent
  }

  # Group 2, at most once every 30 s: housekeeping
  packet Housekeeping id 5 group 2 {
    CdhCore.events.EventsDropped
    CdhCore.$health.PingLateWarnings
    ComCcsds.comQueue.comIngressDropped
    ComCcsds.comQueue.buffIngressDropped
    ComCcsds.comQueue.comManagedDropped
    ComCcsds.comQueue.buffManagedDropped
    ComCcsds.commsBufferManager.TotalBuffs
    ComCcsds.commsBufferManager.CurrBuffs
    ComCcsds.commsBufferManager.HiBuffs
    ComCcsds.commsBufferManager.NoBuffs
    ComCcsds.commsBufferManager.EmptyBuffs
    DataProducts.dpMgr.NumSuccessfulAllocations
    DataProducts.dpMgr.NumFailedAllocations
    DataProducts.dpMgr.NumDataProducts
    DataProducts.dpMgr.NumBytes
    DataProducts.dpWriter.NumBuffersReceived
    DataProducts.dpWriter.NumBytesWritten
    DataProducts.dpWriter.NumSuccessfulWrites
    DataProducts.dpWriter.NumFailedWrites
    DataProducts.dpWriter.NumErrors
    DataProducts.dpBufferManager.TotalBuffs
    DataProducts.dpBufferManager.CurrBuffs
    DataProducts.dpBufferManager.HiBuffs
    DataProducts.dpBufferManager.NoBuffs
    DataProducts.dpBufferManager.EmptyBuffs
    DataProducts.dpBufferAccumulator.BA_NumQueuedBuffers
    FileHandlingCfdp.fileManager.CommandsExecuted
    FileHandlingCfdp.fileManager.Errors
    rateGroup1KHz.RgMaxTime
    rateGroup1KHz.RgCycleSlips
    rateGroup10Hz.RgMaxTime
    rateGroup10Hz.RgCycleSlips
    rateGroup1Hz.RgMaxTime
    rateGroup1Hz.RgCycleSlips
    rateGroup1HzFlush.RgMaxTime
    rateGroup1HzFlush.RgCycleSlips
    Rfm69.spiDriver.SPI_Bytes
    Bmp280.bmpDriver.SPI_Bytes
    NmeaGps.bufferManager.TotalBuffs
    NmeaGps.bufferManager.CurrBuffs
    NmeaGps.bufferManager.HiBuffs
    NmeaGps.bufferManager.NoBuffs
    NmeaGps.bufferManager.EmptyBuffs
    NmeaGps.driver.BytesSent
    NmeaGps.driver.BytesRecv
  }

  # Group 3, at most once every 300 s: large or rarely changing items
  packet CfdpChannels id 6 group 3 {
    FileHandlingCfdp.cfdpManager.ChannelTelemetry
  }

  packet CfdpParameters id 7 group 3 {
    FileHandlingCfdp.cfdpManager.PRM_LOCAL_EID
    FileHandlingCfdp.cfdpManager.PRM_OUTGOING_FILE_CHUNK_SIZE
    FileHandlingCfdp.cfdpManager.PRM_RX_CRC_CALC_BYTES_PER_CYCLE
    FileHandlingCfdp.cfdpManager.PRM_POST_INACTIVITY_SEND_RETRIES
    FileHandlingCfdp.cfdpManager.PRM_FILE_IN_DEFAULT_CHANNEL
    FileHandlingCfdp.cfdpManager.PRM_FILE_IN_DEFAULT_DEST_ENTITY_ID
    FileHandlingCfdp.cfdpManager.PRM_FILE_IN_DEFAULT_CLASS
    FileHandlingCfdp.cfdpManager.PRM_FILE_IN_DEFAULT_KEEP
    FileHandlingCfdp.cfdpManager.PRM_FILE_IN_DEFAULT_PRIORITY
  }

  packet TlmConfig id 9 group 3 {
    CdhCore.tlmSend.GroupConfigs
    CdhCore.tlmSend.SectionEnabled
  }

  packet Versions id 8 group 3 {
    CdhCore.version.FrameworkVersion
    CdhCore.version.ProjectVersion
  }

} omit {
  # PRM_CHANNEL_CONFIG is 1646 bytes at its largest and does not fit a telemetry packet; the
  # version lists are sent as events by version.VERSION.
  CdhCore.version.CustomVersion01
  CdhCore.version.CustomVersion02
  CdhCore.version.CustomVersion03
  CdhCore.version.CustomVersion04
  CdhCore.version.CustomVersion05
  CdhCore.version.CustomVersion06
  CdhCore.version.CustomVersion07
  CdhCore.version.CustomVersion08
  CdhCore.version.CustomVersion09
  CdhCore.version.CustomVersion10
  CdhCore.version.LibraryVersion01
  CdhCore.version.LibraryVersion02
  CdhCore.version.LibraryVersion03
  CdhCore.version.LibraryVersion04
  CdhCore.version.LibraryVersion05
  CdhCore.version.LibraryVersion06
  CdhCore.version.LibraryVersion07
  CdhCore.version.LibraryVersion08
  CdhCore.version.LibraryVersion09
  CdhCore.version.LibraryVersion10
  CdhCore.version.CustomVersion11
  CdhCore.version.CustomVersion12
  CdhCore.version.CustomVersion13
  CdhCore.version.CustomVersion14
  CdhCore.version.CustomVersion15
  CdhCore.version.CustomVersion16
  CdhCore.version.CustomVersion17
  CdhCore.version.CustomVersion18
  CdhCore.version.CustomVersion19
  CdhCore.version.CustomVersion20
  CdhCore.version.CustomVersion21
  CdhCore.version.CustomVersion22
  CdhCore.version.CustomVersion23
  CdhCore.version.CustomVersion24
  CdhCore.version.CustomVersion25
  CdhCore.version.CustomVersion26
  CdhCore.version.CustomVersion27
  CdhCore.version.CustomVersion28
  CdhCore.version.CustomVersion29
  CdhCore.version.CustomVersion30
  CdhCore.version.CustomVersion31
  CdhCore.version.CustomVersion32
  FileHandlingCfdp.cfdpManager.PRM_CHANNEL_CONFIG
}
