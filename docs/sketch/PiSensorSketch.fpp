# Topology sketch for the SSDD (fprime-system-decomposition step 3).
# Not built: elements that do not exist yet are port-only definitions.

module PiSensor {

  @ Pi Camera: on a capture command acquires one JPEG, reads the latest
  @ sensor readings from the telemetry store and writes one product container
  active component PiCamera {
    output port tlmGetOut: Fw.TlmGet
    product request port productRequestOut
    async product recv port productRecvIn
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
  instance rateGroup1KHz: Svc.ActiveRateGroup base id 0x10002000 queue size 10 stack size 65536 priority 41
  instance rateGroup10Hz: Svc.ActiveRateGroup base id 0x10003000 queue size 10 stack size 65536 priority 40
  instance rateGroup1Hz: Svc.ActiveRateGroup base id 0x10004000 queue size 10 stack size 65536 priority 39
  instance posixTime: Svc.PosixTime base id 0x10005000
  instance comRetry: Svc.ComRetry base id 0x10006000
  instance piCamera: PiCamera base id 0x10008000 queue size 5 stack size 65536 priority 30

  topology PiSensor {
    instance CdhCore.Subtopology
    instance ComCcsds.SpacePacketFraming
    instance FileHandlingCfdp.Subtopology
    instance DataProducts.Subtopology
    instance Bmp280.Subtopology
    instance MpuImu.Subtopology
    instance NmeaGps.Subtopology
    instance Rfm69.Subtopology

    instance linuxTimer
    instance rateGroupDriver
    instance rateGroup1KHz
    instance rateGroup10Hz
    instance rateGroup1Hz
    instance posixTime
    instance comRetry
    instance piCamera

    command connections instance CdhCore.cmdDisp
    event connections instance CdhCore.events
    telemetry connections instance CdhCore.tlmSend
    text event connections instance CdhCore.textLogger
    health connections instance CdhCore.$health
    param connections instance FileHandlingCfdp.prmDb
    time connections instance posixTime

    connections RateGroups {
      linuxTimer.CycleOut -> rateGroupDriver.CycleIn
      rateGroupDriver.CycleOut[0] -> rateGroup1KHz.CycleIn
      rateGroupDriver.CycleOut[1] -> rateGroup10Hz.CycleIn
      rateGroupDriver.CycleOut[2] -> rateGroup1Hz.CycleIn
      rateGroup1KHz.RateGroupMemberOut[0] -> Rfm69.rfm69Manager.run
      rateGroup10Hz.RateGroupMemberOut[0] -> ComCcsds.comQueue.run
      rateGroup10Hz.RateGroupMemberOut[1] -> ComCcsds.aggregator.timeout
      rateGroup10Hz.RateGroupMemberOut[2] -> CdhCore.Subtopology.cmdDispRun
      rateGroup10Hz.RateGroupMemberOut[3] -> Bmp280.bmpManager.run
      rateGroup10Hz.RateGroupMemberOut[4] -> MpuImu.imuManager.run
      rateGroup1Hz.RateGroupMemberOut[0] -> CdhCore.Subtopology.tlmSendRun
      rateGroup1Hz.RateGroupMemberOut[1] -> CdhCore.Subtopology.healthRun
      rateGroup1Hz.RateGroupMemberOut[2] -> CdhCore.Subtopology.eventsRun
      rateGroup1Hz.RateGroupMemberOut[3] -> ComCcsds.commsBufferManager.schedIn
      rateGroup1Hz.RateGroupMemberOut[4] -> DataProducts.Subtopology.dpBufferManagerSchedIn
      rateGroup1Hz.RateGroupMemberOut[5] -> DataProducts.Subtopology.dpWriterSchedIn
      rateGroup1Hz.RateGroupMemberOut[6] -> DataProducts.Subtopology.dpMgrSchedIn
      rateGroup1Hz.RateGroupMemberOut[7] -> FileHandlingCfdp.cfdpManager.run1Hz
      rateGroup1Hz.RateGroupMemberOut[8] -> FileHandlingCfdp.fileManager.schedIn
    }

    connections Products {
      # Latest BMP280, MPU6050 and GPS readings with their sample times.
      piCamera.tlmGetOut -> CdhCore.tlmSend.TlmGet
      piCamera.productRequestOut -> DataProducts.Subtopology.productRequestIn
      DataProducts.Subtopology.productResponseOut -> piCamera.productRecvIn
      piCamera.productSendOut -> DataProducts.Subtopology.productSendIn
      # The catalog downlinks stored products by CFDP.
      DataProducts.Subtopology.dpCatFileOut -> FileHandlingCfdp.cfdpManager.fileIn
      FileHandlingCfdp.cfdpManager.fileDoneOut -> DataProducts.Subtopology.dpCatFileDone
    }

    connections Gps {
      # Not connected and not exported by NmeaGps.Subtopology as shipped.
      NmeaGps.driver.allocate -> NmeaGps.bufferManager.bufferGetCallee
      NmeaGps.driver.deallocate -> NmeaGps.bufferManager.bufferSendIn
    }

    connections Communications {
      Rfm69.rfm69Manager.allocate -> ComCcsds.commsBufferManager.bufferGetCallee
      Rfm69.rfm69Manager.deallocate -> ComCcsds.commsBufferManager.bufferSendIn
      ComCcsds.SpacePacketFraming.dataOut -> comRetry.dataIn
      comRetry.dataReturnOut -> ComCcsds.SpacePacketFraming.dataReturnIn
      comRetry.comStatusOut -> ComCcsds.SpacePacketFraming.comStatusIn
      comRetry.dataOut -> Rfm69.rfm69Manager.dataIn
      Rfm69.rfm69Manager.dataReturnOut -> comRetry.dataReturnIn
      Rfm69.rfm69Manager.comStatusOut -> comRetry.comStatusIn
      Rfm69.rfm69Manager.dataOut -> ComCcsds.SpacePacketFraming.dataIn
      ComCcsds.SpacePacketFraming.dataReturnOut -> Rfm69.rfm69Manager.dataReturnIn
    }

    connections Spine {
      CdhCore.Subtopology.eventsPktSend -> ComCcsds.comQueue.comPacketQueueIn[ComCcsds.Ports_ComPacketQueue.EVENTS]
      CdhCore.Subtopology.tlmSendPktSend -> ComCcsds.comQueue.comPacketQueueIn[ComCcsds.Ports_ComPacketQueue.TELEMETRY]
      ComCcsds.fprimeRouter.commandOut -> CdhCore.Subtopology.seqCmdBuff
      CdhCore.Subtopology.seqCmdStatus -> ComCcsds.fprimeRouter.cmdResponseIn
      FileHandlingCfdp.cfdpManager.dataOut[0] -> ComCcsds.comQueue.bufferQueueIn[ComCcsds.Ports_ComBufferQueue.FILE]
      ComCcsds.comQueue.bufferReturnOut[ComCcsds.Ports_ComBufferQueue.FILE] -> FileHandlingCfdp.cfdpManager.dataReturnIn[0]
      ComCcsds.fprimeRouter.fileOut -> FileHandlingCfdp.cfdpManager.dataIn[0]
      FileHandlingCfdp.cfdpManager.dataInReturn[0] -> ComCcsds.fprimeRouter.fileBufferReturnIn
      FileHandlingCfdp.cfdpManager.bufferAllocate[0] -> ComCcsds.commsBufferManager.bufferGetCallee
      FileHandlingCfdp.cfdpManager.bufferDeallocate[0] -> ComCcsds.commsBufferManager.bufferSendIn
    }
  }
}
