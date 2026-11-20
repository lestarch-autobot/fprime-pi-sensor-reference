# ======================================================================
# TlmPacketizerCfg.fpp
# Constants and types for configuring TlmPacketizer (sections, groups, send ports, packet offset type)
# ======================================================================
@ The type of an offset within a telemetry packet buffer.
@ Deliberately defined here (global scope) rather than in FpConfig.fpp so that
@ projects which override FpConfig.fpp continue to build without adding it.
type FwTlmPacketizeOffsetType = U16

module Svc {
    @ Configurable enum supporting multiple resampled telemetry sections
    @ Each section creates output indices for each telemetry group
    enum TelemetrySection {
        # REALTIME is a project-selected name. Default configuration uses REALTIME as this is a common section
        REALTIME, @< OPTIONAL: realtime telemetry downlink through communication stack
        # RECORDED is a project-selected name. Default configuration uses RECORDED as this is a common section
        RECORDED, @< OPTIONAL: recorded telemetry stored on disk for later retrieval
        NUM_SECTIONS,     @< REQUIRED: Counter, leave as last element.
    }

    @ Maximum number of packets the packetizer can be configured with
    constant MAX_PACKETIZER_PACKETS = 50

    @ Greatest packet group
    constant MAX_CONFIGURABLE_TLMPACKETIZER_GROUP = 3

    constant NUM_CONFIGURABLE_TLMPACKETIZER_GROUPS = MAX_CONFIGURABLE_TLMPACKETIZER_GROUP + 1

    @ Number of telemetry output (send) ports. These ports are all the outputs. Each section/group uses the configuration
    @ TELEMETRY_SEND_PORTS to determine which port to send based on the group and section.
    @
    @ This default configuration uses one port per section
    constant TELEMETRY_SEND_PORTS = TelemetrySection.NUM_SECTIONS

    @ Telemetry Output Ports - 2D array of [Section][Group] FwIndexType indicating which port to send telemetry on for a given
    @ section/group. The values must be greater than or equal to 0 and less than TELEMETRY_SEND_PORTS.
    @
    @ This default configuration sends all telemetry on port 0 restoring the original TlmPacketizer behavior.
    constant TELEMETRY_SEND_PORT_MAPPING = [
        [0, 0, 0, 0],
        [1, 1, 1, 1],
    ]

    @ PiSensor: only the REALTIME section is connected (radio downlink); RECORDED stays disabled.
    constant TELEMETRY_SECTION_ENABLED_DEFAULTS = [Fw.Enabled.ENABLED, Fw.Enabled.DISABLED]

    @ PiSensor group rates, in telemetry cycles (1 Hz), sized by docs/link-budget.md.
    @ Every group sends a packet only when one of its channels was written since the last send
    @ (ON_CHANGE_MIN): a sensor that stops producing readings stops being downlinked.
    @ Group 0: sensor readings, every cycle (REQ-PiSensor-001 to -003, -012)
    constant GROUP_0_CONFIG = { sendState = TlmSendState.INHERIT_FROM_PARENT, rates = { rateLogic = RateLogic.ON_CHANGE_MIN, min = 0, max = 0 } }
    @ Group 1: link and command counters, at most once every 5 cycles
    constant GROUP_1_CONFIG = { sendState = TlmSendState.INHERIT_FROM_PARENT, rates = { rateLogic = RateLogic.ON_CHANGE_MIN, min = 5, max = 0 } }
    @ Group 2: housekeeping, at most once every 30 cycles
    constant GROUP_2_CONFIG = { sendState = TlmSendState.INHERIT_FROM_PARENT, rates = { rateLogic = RateLogic.ON_CHANGE_MIN, min = 30, max = 0 } }
    @ Group 3: large and rarely changing items, at most once every 300 cycles
    constant GROUP_3_CONFIG = { sendState = TlmSendState.INHERIT_FROM_PARENT, rates = { rateLogic = RateLogic.ON_CHANGE_MIN, min = 300, max = 0 } }

    @ Default value of the SECTION_CONFIGS parameter: [section][group]
    constant TELEMETRY_SECTION_DEFAULTS = [
        # REALTIME section
        [ GROUP_0_CONFIG, GROUP_1_CONFIG, GROUP_2_CONFIG, GROUP_3_CONFIG ],
        # RECORDED section (disabled, not connected)
        [ GROUP_0_CONFIG, GROUP_1_CONFIG, GROUP_2_CONFIG, GROUP_3_CONFIG ]
    ]
}
