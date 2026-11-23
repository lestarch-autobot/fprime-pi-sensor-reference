# Members of the PiSensor topology that do not depend on the link: included by topologyTcp.fpp and
# topologyRfm69.fpp (PiSensor/CMakeLists.txt, PISENSOR_COM).

    instance CdhCore.Subtopology
    instance ComCcsds.FramingSubtopology
    instance FileHandlingCfdp.Subtopology
    instance DataProducts.Subtopology
    instance Bmp280.Subtopology
    instance MpuImu.Subtopology
    instance NmeaGps.Subtopology

    instance linuxTimer
    instance rateGroupDriver
    instance rateGroup1KHz
    instance rateGroup10Hz
    instance rateGroup1Hz
    instance rateGroup1HzFlush
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

      rateGroupDriver.CycleOut[Ports_RateGroups.rateGroup1KHz] -> rateGroup1KHz.CycleIn

      rateGroupDriver.CycleOut[Ports_RateGroups.rateGroup10Hz] -> rateGroup10Hz.CycleIn
      rateGroup10Hz.RateGroupMemberOut[0] -> ComCcsds.comQueue.run
      rateGroup10Hz.RateGroupMemberOut[1] -> CdhCore.Subtopology.cmdDispRun
      rateGroup10Hz.RateGroupMemberOut[2] -> Bmp280.bmpManager.run
      rateGroup10Hz.RateGroupMemberOut[3] -> MpuImu.imuManager.run

      # A frame that is not full is sent once per second, 250 ms after the telemetry packets of that
      # second were produced (rateGroup1Hz); a full frame is sent at once. With the catalog rate
      # (10 Hz) a burst of events put two frames ahead of the sensor packets (docs/link-budget.md).
      rateGroupDriver.CycleOut[Ports_RateGroups.rateGroup1HzFlush] -> rateGroup1HzFlush.CycleIn
      rateGroup1HzFlush.RateGroupMemberOut[0] -> ComCcsds.aggregator.timeout

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
      # Downlink: TM frames to the retry component; from there to the link of the variant
      ComCcsds.FramingSubtopology.dataOut -> comRetry.dataIn
      comRetry.dataReturnOut -> ComCcsds.FramingSubtopology.dataReturnIn
      comRetry.comStatusOut -> ComCcsds.FramingSubtopology.comStatusIn
    }

    connections DataProducts {
      DataProducts.Subtopology.dpCatFileOut -> FileHandlingCfdp.cfdpManager.fileIn
      FileHandlingCfdp.cfdpManager.fileDoneOut -> DataProducts.Subtopology.dpCatFileDone
    }

    connections Camera {
      piCamera.tlmGetOut -> CdhCore.tlmSend.TlmGet
      piCamera.productGetOut -> DataProducts.Subtopology.productGetIn
      piCamera.productSendOut -> DataProducts.Subtopology.productSendIn
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
