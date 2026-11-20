# PiSensor link budget (RFM69 downlink)

Each figure is marked [V] verified (in the source at the cited place, or measured on the bench
by the session named) or [I] inferred. Bench measurements of this configuration are recorded
in `docs/ledger.md`, not here.

## Capacity

| Item | Value | Basis |
|---|---|---|
| TM frame | 255 bytes | [V] `PiSensor/project/config/ComCfg.fpp` `TmFrameFixedSize` |
| TM frame data field | 247 bytes | [V] `lib/fprime/default/config/CfdpCfg.fpp` comment: 1024-byte frame leaves 1016 |
| Frame period | 0.625 s (1.6 frames/s) | [V] `Rfm69Manager.hpp` `TX_TX_HOLDOFF_TICKS = 500` at the 1 kHz `run`; ~0.125 s airtime measured by the harness session |
| Capacity C | 395 bytes/s of space packets | 1.6 x 247 |

Space packets span frames (`ComCcsdsConfig.fpp` `enablePacketSpanning = true`), so the budget
is in bytes per second, not packets per frame. A frame that the aggregator sends on its
time-out before it is full carries idle fill; when the radio is the bottleneck the aggregator
fills frames completely [I].

## Sources

A telemetry packet is 6 (space packet header) + 2 (descriptor) + 2 (packet id) + 11 (time) =
21 bytes plus its channels [V `Svc/TlmPacketizer/TlmPacketizer.cpp`]. Channel sizes are from
the dictionary [V]. A group sends a packet only if a channel in it was written since the
last send, and not more often than its period (`TlmPacketizerCfg.fpp`, `ON_CHANGE_MIN`).

| Source | Packet (bytes) | Period (s) | bytes/s |
|---|---|---|---|
| `Bmp` (bmpManager.Reading, 12) | 33 | 1 | 33 |
| `Imu` (imuManager.Reading, 28) | 49 | 1 | 49 |
| `Gps` (gpsManager.Reading, 24) | 45 | 1 | 45 |
| `Link` (radio, command, queue, camera, catalog counters) | 82 | 5 | 16 |
| `Housekeeping` (43 channels) | 229 | 30 | 8 |
| `CfdpChannels`, `CfdpParameters`, `Versions`, `TlmConfig` | 253, 42, 105, 103 | 300 | 2 |
| Events (not rate limited; a command gives 2, about 40 bytes each) | | | about 10 allowed |
| CFDP File Data PDU: 6 + 2 + 16 + 4 + 128 file bytes | 156 | 1 | 156 |

## Budget

| Condition | bytes/s | Share of C | Margin |
|---|---|---|---|
| Idle: sensors 127 + link 16 + housekeeping 10 + events 10 | 163 | 41 % | 59 % |
| Downlink: idle 163 + file 156 | 319 | 81 % | 19 % |

- Idle is under the 60 % target. The sensor packets are sent every second, so a reception gap
  is one second plus at most one frame period and the aggregator time-out [I]; REQ-PiSensor-001
  to -003 allow 2 s.
- During a downlink the telemetry queue is served before the file queue (`ComCcsdsConfig.fpp`
  `QueuePriorities`: events 0, telemetry 1, file 2; `Svc.ComQueue` serves 0 first [V
  `ComQueue.cpp`]; it was telemetry 2, file 1), and the file source is limited to one PDU
  per second, so neither queue builds a backlog.
- A 76,573-byte product is 599 File Data PDUs: about 10 minutes plus the EOF/Finished exchange
  and any retransmission. Each retransmitted PDU costs one second.

## Configuration that follows the budget

| Lever | Where | Value | Was |
|---|---|---|---|
| Telemetry as packets, chosen channels and rates | `project/config/CdhCoreTlmConfig.fpp`, `Top/PiSensorPackets.fppi`, `project/config/TlmPacketizerCfg.fpp` | table above | every written channel, every second (`Svc.TlmChan`) |
| CFDP PDU size | `project/config/CfdpCfg.fpp` `MaxPduSize` | 148 (128 file bytes; the file data size is capped by it [V `TransactionTx.cpp`]) | 1001 |
| CFDP PDUs per 1 Hz cycle | parameter `cfdpManager.ChannelConfig[].max_outgoing_pdus_per_cycle`, `project/config/PrmDb.json` | 1 | 64 |
| CFDP ACK timer / limit on the unit | parameter `cfdpManager.ChannelConfig[].ack_timer`, `ack_limit` | 10 s / 10 | 2 s / 10 |
| Queue order | `project/config/ComCcsdsConfig.fpp` `QueuePriorities` | events 0, telemetry 1, file 2 | events 0, file 1, telemetry 2 |
| Product directory | `project/config/DataProductsConfig.fpp` `Paths` | `dp` (product path 39 characters) | `./DpCat` (44) |

The parameters are loaded at start-up from `PrmDb.dat` in the working directory
(`FileHandlingCfdp.prmDb`). Build it from `PiSensor/project/config/PrmDb.json`:

```sh
fprime-prm-write dat --dictionary build-artifacts/Linux/PiSensor/dict/PiSensorTopologyDictionary.json \
    --output PrmDb.dat PiSensor/project/config/PrmDb.json
```

and place it beside where `PiSensor` is started. Without the file the unit sends up to 64 PDUs
per second into a link that carries two; the transfer then depends on `BuffersExhausted`
back-pressure and retransmission.

## Ground (bench set-up, YAMCS `CfdpService`)

The end-of-file exchange crosses the link in both directions with a 0.5 s hold-off each way
and behind queued frames. Set in the bench YAMCS configuration: `inactivityTimeout` at least
60000 ms, `eofAckTimeout` / `finAckTimeout` at least 10000 ms, `nakTimeout` at least 10000 ms,
`immediateNak: false` (a frame lost on the radio then costs one NAK round rather than a NAK per
gap while frames are still in flight).

## Uplink

A command string argument holds at most `FW_CMD_STRING_MAX_SIZE` = 40 characters
[V `lib/fprime/default/config/FpConstants.fpp`, `Fw/Cmd/CmdString.hpp`]; a longer one fails
deserialization and the command is answered `FORMAT_ERROR` [V generated command dispatch].
The observed limit (67-byte TC frame accepted, 71-byte rejected) is this 40-character limit
(27 bytes of frame, packet and command overhead + 40) [I], not a radio limit: a truncated
radio packet would fail the TC frame check and give no command response. The product path is
therefore shortened to 39 characters. Whether TC frames longer than 67 bytes cross the radio
is not established and no command of the test plan needs one.

## Not within project configuration

- The 0.5 s transmit hold-off (`Rfm69Manager.hpp`) sets C. The budget closes with it.
- Picture size: `PICTURE_WIDTH`, `PICTURE_HEIGHT`, `JPEG_QUALITY` are constants of
  `Components/PiCamera/PiCamera.fpp`; `piCamera.configure` takes no size or quality.
