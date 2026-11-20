module CdhCore{

    # PiSensor: telemetry is downlinked as packets (Svc.TlmPacketizer) rather than as every
    # written channel (Svc.TlmChan), so that what goes over the RFM69 link, and how often, is
    # chosen by the packet list in PiSensor/Top/PiSensorPackets.fppi and the group rates in
    # TlmPacketizerCfg.fpp. See docs/link-budget.md.
    instance tlmSend: Svc.TlmPacketizer base id CdhCoreConfig.BASE_ID + 0x06000 \
        queue size CdhCoreConfig.QueueSizes.tlmSend \
        stack size CdhCoreConfig.StackSizes.tlmSend \
        priority CdhCoreConfig.Priorities.tlmSend \
        cpu CdhCoreConfig.CpuAffinities.tlmSend \
    {
        phase Fpp.ToCpp.Phases.configComponents """
        CdhCore::tlmSend.setPacketList(
            PiSensor::PiSensor_PiSensorPacketsTlmPackets::packetList,
            PiSensor::PiSensor_PiSensorPacketsTlmPackets::omittedChannels,
            3  // every group sends; the group rates are in TlmPacketizerCfg.fpp
        );
        """
    }
}
