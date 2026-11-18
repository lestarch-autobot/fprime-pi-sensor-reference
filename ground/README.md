# Ground system (prototype, TCP)

The ground system is fprime-yamcs at the pinned ref (`docs/ledger.md`). `yamcs/etc` holds the
project's changes to its default configuration: HTTP port 8190 and the same URL passed to the
two helper processes, so that it can run beside another YAMCS on a shared workstation.

```sh
cp -r <site-packages>/fprime_yamcs/yamcs/src/main/yamcs yamcs-config
cp ground/yamcs/etc/*.yaml yamcs-config/etc/
fprime-yamcs -n --dictionary <PiSensorTopologyDictionary.json> \
    --yamcs-config-dir $PWD/yamcs-config --yamcs-data-dir $PWD/yamcs-data \
    --udp-downlink-port 51000 --udp-uplink-port 51001 --udp-tm-inject-port 51002 \
    --tcp-fast-port 51050 --skip-browser-open
```

The deployment connects to it with `PiSensor -a <ground host> -p 51050`.

## CFDP

`yamcs/etc/cfdp.sql` and the `CfdpService` entry give the ground a CFDP class 2 entity
(ground 100, flight 42). `sQLFile` is read relative to the directory YAMCS starts in; give
its absolute path if the server is started elsewhere. Downlinked files land in the bucket
`cfdpDown`.

Before the first downlink set the flight chunk size (the default asserts in the framer):

```sh
PiSensor.cfdpManager.OutgoingFileChunkSize_PRM_SET 480
PiSensor.cfdpManager.SendFile 0 100 CLASS_2 KEEP 0 <source, 40 characters at most> <name>
```
