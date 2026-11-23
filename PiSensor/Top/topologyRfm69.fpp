module PiSensor {

  enum Ports_RateGroups {
    rateGroup1KHz
    rateGroup10Hz
    rateGroup1Hz
    rateGroup1HzFlush
  }

  @ Base deployment: inherited elements only, TM and TC frames over the RFM69
  @ Base deployment: inherited elements only, TM and TC frames over the RFM69
  deployment topology PiSensor {

    include "PiSensorCommon.fppi"

    instance Rfm69.Subtopology

    include "PiSensorPackets.fppi"

    connections Radio {
      rateGroup1KHz.RateGroupMemberOut[0] -> Rfm69.rfm69Manager.run
      Rfm69.rfm69Manager.allocate -> ComCcsds.commsBufferManager.bufferGetCallee
      Rfm69.rfm69Manager.deallocate -> ComCcsds.commsBufferManager.bufferSendIn
      # Downlink: TM frames from the retry component to the radio
      comRetry.dataOut -> Rfm69.rfm69Manager.dataIn
      Rfm69.rfm69Manager.dataReturnOut -> comRetry.dataReturnIn
      Rfm69.rfm69Manager.comStatusOut -> comRetry.comStatusIn
      # Uplink: one TC frame per radio packet
      Rfm69.rfm69Manager.dataOut -> ComCcsds.FramingSubtopology.dataIn
      ComCcsds.FramingSubtopology.dataReturnOut -> Rfm69.rfm69Manager.dataReturnIn
    }
  }
}
