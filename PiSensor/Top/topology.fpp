module PiSensor {

  enum Ports_RateGroups {
    rateGroup10Hz
    rateGroup1Hz
  }

  @ GPS subtopology: the members of NmeaGps.Subtopology, with the sentence
  @ path from the accumulator to the GPS adapter left open for sensorMonitor
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
    }
  }

  @ File handling subtopology: the member components of the catalog
  @ FileHandlingCfdp.Subtopology, instantiated here because the catalog
  @ instance of cfdpManager does not compile at the pinned ref
  topology PiFileHandling {
    instance cfdpManager
    instance fileManager
    instance prmDb
  }

  @ Base deployment: inherited elements only, prototype link over TCP
  deployment topology PiSensor {

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
    instance sysTester

    command connections instance CdhCore.cmdDisp
    event connections instance CdhCore.events
    telemetry connections instance CdhCore.tlmSend
    text event connections instance CdhCore.textLogger
    health connections instance CdhCore.$health
    param connections instance prmDb
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
      rateGroup1Hz.RateGroupMemberOut[7] -> cfdpManager.run1Hz
      rateGroup1Hz.RateGroupMemberOut[8] -> fileManager.schedIn
      rateGroup1Hz.RateGroupMemberOut[9] -> sysTester.run
    }

    connections Sensors {
      # Placeholder for sensorMonitor: the sentence path is closed directly.
      NmeaGps.frameAccumulator.dataOut -> NmeaGps.gpsAdapter.commLikeIn
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

    connections Spine {
      CdhCore.Subtopology.eventsPktSend -> ComCcsds.Subtopology.comPacketQueueIn[ComCcsds.Ports_ComPacketQueue.EVENTS]
      CdhCore.Subtopology.tlmSendPktSend -> ComCcsds.Subtopology.comPacketQueueIn[ComCcsds.Ports_ComPacketQueue.TELEMETRY]
      ComCcsds.Subtopology.commandOut -> CdhCore.Subtopology.seqCmdBuff
      CdhCore.Subtopology.seqCmdStatus -> ComCcsds.Subtopology.cmdResponseIn
      cfdpManager.dataOut[0] -> ComCcsds.Subtopology.bufferQueueIn[ComCcsds.Ports_ComBufferQueue.FILE]
      ComCcsds.Subtopology.bufferReturnOut[ComCcsds.Ports_ComBufferQueue.FILE] -> cfdpManager.dataReturnIn[0]
      ComCcsds.Subtopology.fileUplinkOut -> cfdpManager.dataIn[0]
      cfdpManager.dataInReturn[0] -> ComCcsds.Subtopology.fileUplinkReturnIn
      cfdpManager.bufferAllocate[0] -> ComCcsds.Subtopology.commsBufferGetCallee
      cfdpManager.bufferDeallocate[0] -> ComCcsds.Subtopology.commsBufferSendIn
    }
  }
}
