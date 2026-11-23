# fprime-pi-sensor-reference
F Prime Raspberry Pi 5 sensor reference: BMP280, MPU6050, Pi Camera, NMEA GPS, CFDP data products over RFM69

## Link between the deployment and the ground

`PISENSOR_COM` (CMake cache option of `PiSensor/CMakeLists.txt`) selects the link at generate time:

| Value | Link | Topology files |
|---|---|---|
| `TCP` (default) | `Drv.TcpClient` (`comDriver`) behind `Svc.ComStub` (`comStub`). The deployment connects to the ground at the address and port of `PiSensor -a <address> -p <port>`; both are required and have no default. | `Top/topologyTcp.fpp`, `Top/instancesTcp.fpp`, `Top/PiSensorPacketsTcp.fppi` |
| `RFM69` | `Rfm69.Subtopology`, as up to `5999d5f` (`fprime-util generate -DPISENSOR_COM=RFM69`). | `Top/topologyRfm69.fpp`, `Top/PiSensorPackets.fppi` |

`Top/PiSensorCommon.fppi` holds everything the two share. The link is behind `comRetry` in both; framing
(`ComCcsds.FramingSubtopology`, 255-byte TM frames), telemetry packets and rates, queue priorities, the CFDP
configuration, `PrmDb.json` and the product directory are the same.

Differences of the TCP variant, by human ruling of 2026-11-23 ("Ok, please switch to TCP, and continue
development w/o the radio"), not reviewed:

- REQ-PiSensor-010 (link only through the RFM69 packet radio) is not met and `docs/ssdd.md` still describes the
  radio.
- The six channels of the RFM69 subtopology are not in the dictionary or in packet `G1Link`.
- `rateGroup1KHz` has no member: only the radio used it. It stays, with its health ping and the 1 kHz base
  cycle.
- Nothing limits the frame rate as the 0.5 s transmit hold-off of the radio did (`docs/link-budget.md`); the
  queues and CFDP settings were not retuned.
- TC frames arrive as a byte stream instead of one frame per radio packet; the frame accumulator of
  `ComCcsds.FramingSubtopology` finds them.
