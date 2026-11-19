module PiSensor {

  enum Ports_RateGroups {
    rateGroup1KHz
    rateGroup10Hz
    rateGroup1Hz
  }

  @ Base deployment: inherited elements only, TM and TC frames over the RFM69
  deployment topology PiSensor {

    instance CdhCore.Subtopology
    instance ComCcsds.FramingSubtopology
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

    command connections instance CdhCore.cmdDisp
    event connections instance CdhCore.events
    telemetry connections instance CdhCore.tlmSend
    text event connections instance CdhCore.textLogger
    health connections instance CdhCore.$health
    param connections instance FileHandlingCfdp.prmDb
    time connections instance posixTime

    connections RateGroups {
      linuxTimer.CycleOut -> rateGroupDriver.CycleIn

      rateGroupDriver.CycleOut[Ports_RateGroups.rateGroup1KHz] -> rateGroup1KHz.CycleIn
      rateGroup1KHz.RateGroupMemberOut[0] -> Rfm69.rfm69Manager.run

      rateGroupDriver.CycleOut[Ports_RateGroups.rateGroup10Hz] -> rateGroup10Hz.CycleIn
      rateGroup10Hz.RateGroupMemberOut[0] -> ComCcsds.comQueue.run
      rateGroup10Hz.RateGroupMemberOut[1] -> ComCcsds.aggregator.timeout
      rateGroup10Hz.RateGroupMemberOut[2] -> CdhCore.Subtopology.cmdDispRun
      rateGroup10Hz.RateGroupMemberOut[3] -> Bmp280.bmpManager.run
      rateGroup10Hz.RateGroupMemberOut[4] -> MpuImu.imuManager.run

      rateGroupDriver.CycleOut[Ports_RateGroups.rateGroup1Hz] -> rateGroup1Hz.CycleIn
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

    connections Sensors {
      # Not connected and not exported by NmeaGps.Subtopology as shipped.
      NmeaGps.driver.allocate -> NmeaGps.bufferManager.bufferGetCallee
      NmeaGps.driver.deallocate -> NmeaGps.bufferManager.bufferSendIn
    }

    connections Communications {
      Rfm69.rfm69Manager.allocate -> ComCcsds.commsBufferManager.bufferGetCallee
      Rfm69.rfm69Manager.deallocate -> ComCcsds.commsBufferManager.bufferSendIn
      # Downlink: TM frames through the retry component to the radio
      ComCcsds.FramingSubtopology.dataOut -> comRetry.dataIn
      comRetry.dataReturnOut -> ComCcsds.FramingSubtopology.dataReturnIn
      comRetry.comStatusOut -> ComCcsds.FramingSubtopology.comStatusIn
      comRetry.dataOut -> Rfm69.rfm69Manager.dataIn
      Rfm69.rfm69Manager.dataReturnOut -> comRetry.dataReturnIn
      Rfm69.rfm69Manager.comStatusOut -> comRetry.comStatusIn
      # Uplink: one TC frame per radio packet
      Rfm69.rfm69Manager.dataOut -> ComCcsds.FramingSubtopology.dataIn
      ComCcsds.FramingSubtopology.dataReturnOut -> Rfm69.rfm69Manager.dataReturnIn
    }

    connections DataProducts {
      DataProducts.Subtopology.dpCatFileOut -> FileHandlingCfdp.cfdpManager.fileIn
      FileHandlingCfdp.cfdpManager.fileDoneOut -> DataProducts.Subtopology.dpCatFileDone
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
