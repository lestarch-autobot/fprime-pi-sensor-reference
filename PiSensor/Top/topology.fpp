module PiSensor {

  enum Ports_RateGroups {
    rateGroup10Hz
    rateGroup1Hz
  }

  @ Base deployment: inherited elements only, prototype link over TCP
  deployment topology PiSensor {

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

    command connections instance CdhCore.cmdDisp
    event connections instance CdhCore.events
    telemetry connections instance CdhCore.tlmSend
    text event connections instance CdhCore.textLogger
    health connections instance CdhCore.$health
    param connections instance FileHandlingCfdp.prmDb
    time connections instance posixTime

    connections RateGroups {
      linuxTimer.CycleOut -> rateGroupDriver.CycleIn

      rateGroupDriver.CycleOut[Ports_RateGroups.rateGroup10Hz] -> rateGroup10Hz.CycleIn
      rateGroup10Hz.RateGroupMemberOut[0] -> ComCcsds.Subtopology.comQueueRun
      rateGroup10Hz.RateGroupMemberOut[1] -> ComCcsds.Subtopology.aggregatorTimeout
      rateGroup10Hz.RateGroupMemberOut[2] -> CdhCore.Subtopology.cmdDispRun
      rateGroup10Hz.RateGroupMemberOut[3] -> Bmp280.bmpManager.run
      rateGroup10Hz.RateGroupMemberOut[4] -> MpuImu.imuManager.run

      rateGroupDriver.CycleOut[Ports_RateGroups.rateGroup1Hz] -> rateGroup1Hz.CycleIn
      rateGroup1Hz.RateGroupMemberOut[0] -> CdhCore.Subtopology.tlmSendRun
      rateGroup1Hz.RateGroupMemberOut[1] -> CdhCore.Subtopology.healthRun
      rateGroup1Hz.RateGroupMemberOut[2] -> CdhCore.Subtopology.eventsRun
      rateGroup1Hz.RateGroupMemberOut[3] -> ComCcsds.Subtopology.bufferManagerSchedIn
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
      tcpLink.allocate -> ComCcsds.Subtopology.commsBufferGetCallee
      tcpLink.deallocate -> ComCcsds.Subtopology.commsBufferSendIn
      tcpLink.$recv -> ComCcsds.Subtopology.drvReceiveIn
      ComCcsds.Subtopology.drvReceiveReturnOut -> tcpLink.recvReturnIn
      ComCcsds.Subtopology.drvSendOut -> tcpLink.$send
      tcpLink.ready -> ComCcsds.Subtopology.drvConnected
      # The radio is instantiated but not scheduled in the prototype configuration.
      Rfm69.rfm69Manager.allocate -> ComCcsds.Subtopology.commsBufferGetCallee
      Rfm69.rfm69Manager.deallocate -> ComCcsds.Subtopology.commsBufferSendIn
    }

    connections DataProducts {
      DataProducts.Subtopology.dpCatFileOut -> FileHandlingCfdp.cfdpManager.fileIn
      FileHandlingCfdp.cfdpManager.fileDoneOut -> DataProducts.Subtopology.dpCatFileDone
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
      FileHandlingCfdp.cfdpManager.bufferAllocate[0] -> ComCcsds.Subtopology.commsBufferGetCallee
      FileHandlingCfdp.cfdpManager.bufferDeallocate[0] -> ComCcsds.Subtopology.commsBufferSendIn
    }
  }
}
