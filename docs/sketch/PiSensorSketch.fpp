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
  @ with validity, reports sensor loss and return, serves samples to products
  passive component SensorMonitor {
    output port tlmGetOut: Fw.TlmGet
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
  instance piCamera: PiCamera base id 0x10008000 queue size 5 stack size 65536 priority 30
  instance sensorMonitor: SensorMonitor base id 0x10009000
  instance productManager: ProductManager base id 0x1000A000 queue size 10 stack size 65536 priority 31

  topology PiSensor {
    instance CdhCore.Subtopology
    instance ComCcsds.Subtopology
    instance FileHandlingCfdp.Subtopology
    instance DataProducts.Subtopology
    instance Bmp280.Subtopology
    instance MpuImu.Subtopology
    instance NmeaGps.Subtopology
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
    param connections instance FileHandlingCfdp.prmDb
    time connections instance posixTime

    connections RateGroups {
      linuxTimer.CycleOut -> rateGroupDriver.CycleIn
      rateGroupDriver.CycleOut[0] -> rateGroup10Hz.CycleIn
      rateGroupDriver.CycleOut[1] -> rateGroup1Hz.CycleIn
      # Members: see the instance table in docs/ssdd.md.
    }

    connections Sensors {
      # Latest BMP280, MPU6050 and GPS readings with their sample times.
      # GPS fix status and sentence arrival also reach sensorMonitor; that
      # path is fixed at allocation.
      sensorMonitor.tlmGetOut -> CdhCore.tlmSend.TlmGet
    }

    connections Products {
      productManager.captureOut -> piCamera.captureIn
      piCamera.imageOut -> productManager.imageIn
      productManager.imageReturnOut -> piCamera.imageReturnIn
      productManager.samplesGetOut -> sensorMonitor.samplesGetIn
      productManager.productGetOut -> DataProducts.Subtopology.productGetIn
      productManager.productSendOut -> DataProducts.Subtopology.productSendIn
      DataProducts.dpWriter.dpWrittenOut -> productManager.dpWrittenIn
      productManager.sendFileOut -> FileHandlingCfdp.cfdpManager.fileIn
      FileHandlingCfdp.cfdpManager.fileDoneOut -> productManager.fileDoneIn
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
      FileHandlingCfdp.cfdpManager.dataOut[0] -> ComCcsds.Subtopology.bufferQueueIn[ComCcsds.Ports_ComBufferQueue.FILE]
      ComCcsds.Subtopology.bufferReturnOut[ComCcsds.Ports_ComBufferQueue.FILE] -> FileHandlingCfdp.cfdpManager.dataReturnIn[0]
      ComCcsds.Subtopology.fileUplinkOut -> FileHandlingCfdp.cfdpManager.dataIn[0]
      FileHandlingCfdp.cfdpManager.dataInReturn[0] -> ComCcsds.Subtopology.fileUplinkReturnIn
    }
  }
}
