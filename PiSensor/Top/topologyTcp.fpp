module PiSensor {

  enum Ports_RateGroups {
    rateGroup1KHz
    rateGroup10Hz
    rateGroup1Hz
    rateGroup1HzFlush
  }

  @ Base deployment: inherited elements only, TM and TC frames over the RFM69
  @ Base deployment: inherited elements only, TM and TC frames over a TCP connection to the ground
  deployment topology PiSensor {

    include "PiSensorCommon.fppi"

    instance comStub
    instance comDriver

    include "PiSensorPacketsTcp.fppi"

    connections Tcp {
      comDriver.allocate -> ComCcsds.commsBufferManager.bufferGetCallee
      comDriver.deallocate -> ComCcsds.commsBufferManager.bufferSendIn
      # Downlink: TM frames from the retry component through Svc.ComStub to the TCP connection
      comRetry.dataOut -> comStub.dataIn
      comStub.dataReturnOut -> comRetry.dataReturnIn
      comStub.comStatusOut -> comRetry.comStatusIn
      comStub.drvSendOut -> comDriver.$send
      comDriver.ready -> comStub.drvConnected
      # Uplink: the byte stream of the TCP connection; the frame accumulator finds the TC frames in it
      comDriver.$recv -> comStub.drvReceiveIn
      comStub.drvReceiveReturnOut -> comDriver.recvReturnIn
      comStub.dataOut -> ComCcsds.FramingSubtopology.dataIn
      ComCcsds.FramingSubtopology.dataReturnOut -> comStub.dataReturnIn
    }
  }
}
