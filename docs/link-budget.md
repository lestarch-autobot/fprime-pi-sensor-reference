# PiSensor link budget (RFM69 downlink)

Each figure is marked [V] verified (in the source at the cited place, or measured on the bench
with `fix/link-budget`) or [I] inferred.

## Capacity

| Item | Value | Basis |
|---|---|---|
| TM frame | 255 bytes | [V] `PiSensor/project/config/ComCfg.fpp` `TmFrameFixedSize` |
| TM frame data field | 247 bytes | [V] frame minus 6-byte header and 2-byte error control |
| Frame period | 0.62 s (1.6 frames/s) | [V] `Rfm69Manager.hpp` `TX_TX_HOLDOFF_TICKS = 500` at the 1 kHz `run`, plus airtime; frame spacing 0.62 s measured |
| Capacity C | 395 bytes/s of space packets, in at most 1.6 frames/s | 1.6 x 247 |

Both limits count. Space packets span frames (`ComCcsdsConfig.fpp` `enablePacketSpanning =
true`), so a busy link fills its frames and carries 395 bytes/s. A frame that is sent before it
is full carries idle fill, so a quiet link is limited by the number of frames, not by bytes.

## Sources

A telemetry packet is 6 (space packet header) + 2 (descriptor) + 2 (packet id) + 11 (time) =
21 bytes plus its channels [V sizes seen in the frames on the bench]. A group sends a packet
only if a channel in it was written since the last send, and not more often than its period
(`TlmPacketizerCfg.fpp`, `ON_CHANGE_MIN`).

| Source | Packet (bytes) | Period (s) | bytes/s |
|---|---|---|---|
| `G0Bmp` (bmpManager.Reading) | 33 | 1 | 33 |
| `G0Imu` (imuManager.Reading) | 49 | 1 | 49 |
| `G0Gps` (gpsManager.Reading) | 45 | 1 | 45 |
| `G1Link` (radio, command, queue, camera, catalog counters) | 82 | 5 | 16 |
| `G2Housekeeping` | 237 | 30 | 8 |
| `G3CfdpChannels`, `G3CfdpParameters`, `G3Versions`, `G3TlmConfig` | 253, 42, 105, 103 | 300 | 2 |
| Events (not rate limited; a command gives 2 of about 40 bytes) | | | about 10 allowed |
| CFDP File Data PDU: 6 + 2 + 16 + 4 + 128 file bytes | 156 | 1 | 156 |

## Budget

| Condition | bytes/s | Share of 395 | Frames/s | Share of 1.6 |
|---|---|---|---|---|
| Idle: sensors 127 + link 16 + housekeeping 8 + other 2 + events 10 | 163 | 41 % | 1.0 plus a second frame when a cycle exceeds 247 bytes; 1.08 measured | 68 % |
| Downlink: idle 163 + file 156 | 319 | 81 % | 319 / 247 = 1.3 when frames fill; 1.28 measured | 80 % |

- One frame per second is the least that meets the 2 s requirements with 1 Hz sensors, and it
  is 62.5 % of the frames the hold-off allows: the frame share cannot go below that, however
  few bytes are sent. In bytes, idle is 41 % with a live IMU.
- A 76,573-byte product is 599 File Data PDUs: about 10 minutes. 127,491 bytes took 938 s
  on the bench [V]. Each retransmitted PDU costs one second.

## Timing of a second

The base cycle is 1 kHz (`PiSensorTopology.cpp`, `rateGroupDivisorsSet`).

| When | What | Why |
|---|---|---|
| t | 10 Hz group: the sensor managers write `Reading` | |
| t + 50 ms | 1 Hz group: `tlmSend` makes the packets, `cfdpManager` makes one PDU | on the same cycle as the 10 Hz group the packetizer could miss the sample of that second |
| t + 300 ms | `rateGroup1HzFlush`: `aggregator.timeout` sends the frame if it is not full | at 10 Hz a burst of five events left as two frames ahead of the sensor frame (gap 1.95 to 2.0 s measured) |

A frame that fills is sent at once. `Svc.TlmPacketizer` sends the packets of a cycle in the
order of their names, hence the group prefix: sensor packets are at the head of the frame.
`Svc.ComQueue` serves priority 0 first: telemetry 0, events 1, file 2.

## Configuration that follows the budget

| Lever | Where | Value | Was |
|---|---|---|---|
| Telemetry as packets, chosen channels and rates | `project/config/CdhCoreTlmConfig.fpp`, `Top/PiSensorPackets.fppi`, `project/config/TlmPacketizerCfg.fpp` | table above | every written channel, every second (`Svc.TlmChan`) |
| Queue order | `project/config/ComCcsdsConfig.fpp` `QueuePriorities` | telemetry 0, events 1, file 2 | events 0, file 1, telemetry 2 |
| 1 Hz group phase | `Top/PiSensorTopology.cpp` | offset 50 ms | 0 |
| Partial frame time-out | `Top/topology.fpp`, `Top/instances.fpp` `rateGroup1HzFlush`; `project/config/AcConstants.fpp` `RateGroupDriverRateGroupPorts = 4` | 1 Hz, offset 300 ms | 10 Hz |
| CFDP PDU size | `project/config/CfdpCfg.fpp` `MaxPduSize` | 148 (128 file bytes) | 1001 |
| CFDP PDUs per 1 Hz cycle | parameter `cfdpManager.ChannelConfig[].max_outgoing_pdus_per_cycle`, `project/config/PrmDb.json` | 1 | 64 |
| CFDP ACK timer / limit on the unit | parameter `cfdpManager.ChannelConfig[].ack_timer`, `ack_limit` | 10 s / 10 | 2 s / 10 |
| Product directory | `project/config/DataProductsConfig.fpp` `Paths` | `dp` (product path 39 characters) | `./DpCat` (44) |

## Parameter file

The two CFDP values above exist only as parameters. `FileHandlingCfdp.prmDb` reads `PrmDb.dat`
from the working directory of the process at start-up [V event `PrmFileLoadComplete ...
Records: 1` on the bench]. Build it from `PiSensor/project/config/PrmDb.json` with the
dictionary of the same image (`fprime-prm-write` is installed with the F Prime tools):

```sh
fprime-prm-write dat PiSensor/project/config/PrmDb.json \
    --dictionary build-artifacts/Linux/PiSensor/dict/PiSensorTopologyDictionary.json -o PrmDb.dat
```

Copy `PrmDb.dat` into the directory from which `PiSensor` is started, before starting it. The
file is 125 bytes. Without it the unit uses the defaults: 64 PDUs per second and a 2 s ACK
timer, into a link that carries one or two frames per second.

## Ground (bench set-up, YAMCS `CfdpService`)

Used on the bench, added under `args` of `org.yamcs.cfdp.CfdpService` in
`etc/yamcs.fprime-project.yaml` of the bench YAMCS configuration: `inactivityTimeout: 60000`,
`eofAckTimeout: 10000`, `finAckTimeout: 10000`, `finAckLimit: 10`, `nakTimeout: 20000`,
`nakLimit: 10`, `immediateNak: false`.

## Uplink

A command string argument holds at most `FW_CMD_STRING_MAX_SIZE` = 40 characters
[V `lib/fprime/default/config/FpConstants.fpp`, `Fw/Cmd/CmdString.hpp`]. The product path is
39 characters with the directory `dp`.

## Limits that project configuration does not remove

- The 0.5 s transmit hold-off (`Rfm69Manager.hpp`) sets the 1.6 frames/s.
- About one TM frame in 650 reaches the ground with a wrong frame error control field and is
  discarded by YAMCS [V 2 of 1283 and 2 of 1298 frames in two 20-minute runs]. The telemetry of
  that second is lost and the reception gap of each sensor is then 2.0 s. A second copy of
  each sample would need two frames per second, which the hold-off does not allow.
- Picture size: `PICTURE_WIDTH`, `PICTURE_HEIGHT`, `JPEG_QUALITY` are constants of
  `Components/PiCamera/PiCamera.fpp`; `piCamera.configure` takes no size or quality.
