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
