# Topology sketch for the SSDD (fprime-system-decomposition step 3).
# Not built: elements that do not exist yet are port-only definitions.

module PiSensor {

  @ Request for the latest sample of every metric
  port SamplesGet(context: U32)
  @ Request to acquire one picture
  port CaptureRequest(context: U32)

  @ Pi Camera manager: acquires one JPEG per request
  active component PiCamera {
    async input port captureIn: CaptureRequest
    output port imageOut: Fw.BufferSend
    async input port imageReturnIn: Fw.BufferSend
    output port allocate: Fw.BufferGet
    output port deallocate: Fw.BufferSend
    event port eventOut
    text event port textEventOut
    telemetry port tlmOut
    time get port timeGetOut
  }

  @ Sensor monitor: reads the latest sensor readings, publishes Table 1 telemetry
  @ with validity, reports sensor loss and return, serves samples to products.
  @ Adapter: reads the MPU6050 identity register, and the fix field and
  @ arrival time of each GPS sentence passing through it.
  passive component SensorMonitor {
    output port tlmGetOut: Fw.TlmGet
    output port imuIdentityOut: Drv.I2cWriteRead
    guarded input port gpsSentenceIn: Svc.ComDataWithContext
    output port gpsSentenceOut: Svc.ComDataWithContext
    guarded input port samplesGetIn: SamplesGet
    sync input port run: Svc.Sched
    event port eventOut
    text event port textEventOut
    telemetry port tlmOut
    time get port timeGetOut
  }

  @ Product manager: capture, downlink and delete commands; builds the data product
  active component ProductManager {
    output port captureOut: CaptureRequest
    async input port imageIn: Fw.BufferSend
    output port imageReturnOut: Fw.BufferSend
    output port samplesGetOut: SamplesGet
    async input port dpWrittenIn: Svc.DpWritten
    output port sendFileOut: Svc.SendFileRequest
    async input port fileDoneIn: Svc.SendFileComplete
    async input port run: Svc.Sched
    product get port productGetOut
    product send port productSendOut
    command recv port cmdIn
    command reg port cmdRegOut
    command resp port cmdResponseOut
    event port eventOut
    text event port textEventOut
    telemetry port tlmOut
    time get port timeGetOut
  }

  instance linuxTimer: Svc.LinuxTimer base id 0x10000000
  instance rateGroupDriver: Svc.RateGroupDriver base id 0x10001000
  instance rateGroup10Hz: Svc.ActiveRateGroup base id 0x10002000 queue size 10 stack size 65536 priority 40
  instance rateGroup1Hz: Svc.ActiveRateGroup base id 0x10003000 queue size 10 stack size 65536 priority 39
  instance posixTime: Svc.PosixTime base id 0x10004000
  instance tcpLink: Drv.TcpClient base id 0x10005000
  instance cfdpManager: Svc.Ccsds.Cfdp.CfdpManager base id 0x10010000 queue size 30 stack size 131072 priority 24
  instance fileManager: Svc.FileManager base id 0x10011000 queue size 10 stack size 65536 priority 22
  instance prmDb: Svc.PrmDb base id 0x10012000 queue size 10 stack size 65536 priority 21
  instance piCamera: PiCamera base id 0x10008000 queue size 5 stack size 65536 priority 30
  instance sensorMonitor: SensorMonitor base id 0x10009000
  instance productManager: ProductManager base id 0x1000A000 queue size 10 stack size 65536 priority 31

  @ GPS subtopology: the members of NmeaGps.Subtopology, with the sentence
  @ path from the accumulator to the GPS manager opened for sensorMonitor
  topology PiGps {
    instance NmeaGps.gpsManager
    instance NmeaGps.gpsAdapter
    instance NmeaGps.frameAccumulator
    instance NmeaGps.driverInterface
    instance NmeaGps.driver
    instance NmeaGps.bufferManager

    connections Gps {
      NmeaGps.gpsAdapter.bufferLikeOut -> NmeaGps.gpsManager.dataIn
      NmeaGps.gpsManager.dataReturnOut -> NmeaGps.gpsAdapter.bufferLikeIn
      NmeaGps.frameAccumulator.bufferAllocate -> NmeaGps.bufferManager.bufferGetCallee
      NmeaGps.frameAccumulator.bufferDeallocate -> NmeaGps.bufferManager.bufferSendIn
      NmeaGps.gpsAdapter.commLikeOut -> NmeaGps.frameAccumulator.dataReturnIn
      NmeaGps.driverInterface.commLikeOut -> NmeaGps.frameAccumulator.dataIn
      NmeaGps.frameAccumulator.dataReturnOut -> NmeaGps.driverInterface.commLikeIn
      NmeaGps.driver.$recv -> NmeaGps.driverInterface.byteStreamLikeIn
      NmeaGps.driverInterface.bufferLikeOut -> NmeaGps.driver.recvReturnIn
      NmeaGps.driver.allocate -> NmeaGps.bufferManager.bufferGetCallee
      NmeaGps.driver.deallocate -> NmeaGps.bufferManager.bufferSendIn
    }
  }

  @ File handling subtopology: the three member components of the catalog
  @ FileHandlingCfdp.Subtopology, instantiated by this project
  topology PiFileHandling {
    instance cfdpManager
    instance fileManager
    instance prmDb
  }

  topology PiSensor {
    instance CdhCore.Subtopology
    instance ComCcsds.Subtopology
    instance PiFileHandling
    instance DataProducts.Subtopology
    instance Bmp280.Subtopology
    instance MpuImu.Subtopology
    instance PiGps
    instance Rfm69.Subtopology

    instance linuxTimer
    instance rateGroupDriver
    instance rateGroup10Hz
    instance rateGroup1Hz
    instance posixTime
    instance tcpLink
    instance piCamera
    instance sensorMonitor
    instance productManager

    command connections instance CdhCore.cmdDisp
    event connections instance CdhCore.events
    telemetry connections instance CdhCore.tlmSend
    text event connections instance CdhCore.textLogger
    health connections instance CdhCore.$health
    param connections instance prmDb
    time connections instance posixTime

    connections RateGroups {
      linuxTimer.CycleOut -> rateGroupDriver.CycleIn
      rateGroupDriver.CycleOut[0] -> rateGroup10Hz.CycleIn
      rateGroupDriver.CycleOut[1] -> rateGroup1Hz.CycleIn
      # Members: see the instance table in docs/ssdd.md.
    }

    connections Sensors {
      # Latest BMP280, MPU6050 and GPS readings with their sample times.
      sensorMonitor.tlmGetOut -> CdhCore.tlmSend.TlmGet
      # MPU6050 identity register, through the IMU bus driver.
      sensorMonitor.imuIdentityOut -> MpuImu.imuDriver.writeRead
      # Each GPS sentence passes through sensorMonitor (fix field, arrival time).
      NmeaGps.frameAccumulator.dataOut -> sensorMonitor.gpsSentenceIn
      sensorMonitor.gpsSentenceOut -> NmeaGps.gpsAdapter.commLikeIn
    }

    connections Products {
      productManager.captureOut -> piCamera.captureIn
      piCamera.imageOut -> productManager.imageIn
      productManager.imageReturnOut -> piCamera.imageReturnIn
      productManager.samplesGetOut -> sensorMonitor.samplesGetIn
      productManager.productGetOut -> DataProducts.Subtopology.productGetIn
      productManager.productSendOut -> DataProducts.Subtopology.productSendIn
      DataProducts.dpWriter.dpWrittenOut -> productManager.dpWrittenIn
      productManager.sendFileOut -> cfdpManager.fileIn
      cfdpManager.fileDoneOut -> productManager.fileDoneIn
    }

    connections Communications {
      # Prototype configuration: TCP byte stream under the CCSDS stack.
      tcpLink.allocate -> ComCcsds.Subtopology.commsBufferGetCallee
      tcpLink.deallocate -> ComCcsds.Subtopology.commsBufferSendIn
      tcpLink.$recv -> ComCcsds.Subtopology.drvReceiveIn
      ComCcsds.Subtopology.drvReceiveReturnOut -> tcpLink.recvReturnIn
      ComCcsds.Subtopology.drvSendOut -> tcpLink.$send
      tcpLink.ready -> ComCcsds.Subtopology.drvConnected
      # Flight configuration: ComCcsds.FramingSubtopology with Rfm69.Subtopology
      # in place of comStub and tcpLink; wired in the base-deployment lane.
      Rfm69.rfm69Manager.allocate -> ComCcsds.Subtopology.commsBufferGetCallee
      Rfm69.rfm69Manager.deallocate -> ComCcsds.Subtopology.commsBufferSendIn
    }

    connections Spine {
      CdhCore.Subtopology.eventsPktSend -> ComCcsds.Subtopology.comPacketQueueIn[ComCcsds.Ports_ComPacketQueue.EVENTS]
      CdhCore.Subtopology.tlmSendPktSend -> ComCcsds.Subtopology.comPacketQueueIn[ComCcsds.Ports_ComPacketQueue.TELEMETRY]
      ComCcsds.Subtopology.commandOut -> CdhCore.Subtopology.seqCmdBuff
      CdhCore.Subtopology.seqCmdStatus -> ComCcsds.Subtopology.cmdResponseIn
      cfdpManager.dataOut[0] -> ComCcsds.Subtopology.bufferQueueIn[ComCcsds.Ports_ComBufferQueue.FILE]
      ComCcsds.Subtopology.bufferReturnOut[ComCcsds.Ports_ComBufferQueue.FILE] -> cfdpManager.dataReturnIn[0]
      ComCcsds.Subtopology.fileUplinkOut -> cfdpManager.dataIn[0]
      cfdpManager.dataInReturn[0] -> ComCcsds.Subtopology.fileUplinkReturnIn
    }
  }
}
