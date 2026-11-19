#!/usr/bin/env python3
"""Bench `recorder` line of bench.json: the record of one run, taken from fprime-yamcs.

fth's recorder is `fprime-cli events`; here the ground system is YAMCS, so this process subscribes to
YAMCS and writes under `<logs>` (= record/raw):

  fprime-cli-yamcs/event.log     one line per event, in the line format `fth export` parses
  fprime-cli-yamcs/channel.log   one line per telemetry sample, same
  yamcs/events.jsonl             the YAMCS events as received (all fields)
  yamcs/channels.jsonl           the YAMCS parameter values as received
  yamcs/timetags.jsonl           F Prime time tag of each event packet beside YAMCS's generation time
  yamcs/links.jsonl              YAMCS link counters, once a second
  cfdp.json                      YAMCS file transfer records + the ground time each was first seen and seen finished
  frames.json                    TM frames handed to YAMCS (bench bridge log) + YAMCS link counters
  files/<name>                   each file YAMCS received by CFDP, copied from its bucket when complete
  dictionary.json                the dictionary this run decodes with
  commands.json, yamcs/events-archive.json   YAMCS command history and event archive, written at stop

Each line of event.log / channel.log carries the FSW time (YAMCS generation time minus `--gen-offset`,
see README) and, in the parenthesised field, the ground reception time `rx=<UTC epoch seconds>`.
Stops on SIGTERM / SIGINT after a last export.
"""
import argparse
import datetime
import hashlib
import json
import os
import signal
import struct
import sys
import threading
import time
from pathlib import Path

TERMINAL = ("COMPLETED", "FAILED", "CANCELLED")
EVENT_TIME_TAG_OFFSET = 6 + 2 + 4 + 2 + 1  # space packet header, descriptor, event id, time base, context


# ---------------------------------------------------------------- pure formatting (unit tested)
def epoch(value) -> float:
    """UTC epoch seconds of a datetime (naive = UTC) or an ISO-8601 string."""
    if isinstance(value, str):
        value = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.timestamp()


def one_line(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")


def log_name(deployment: str, qualified: str) -> str:
    """`CdhCore.cmdDisp.OpCodeCompleted` -> `<deployment>.cmdDisp.OpCodeCompleted` (the name fth looks for)."""
    return ".".join([deployment] + qualified.split(".")[-2:]) if deployment else qualified


def event_line(ev: dict, gen_offset: float, deployment: str = "") -> str:
    """`ev`: {type, message, generationTime, receptionTime, extra{fprime_severity, fprime_event_id}}."""
    extra = ev.get("extra") or {}
    name = extra.get("fprime_event_name") or ev["type"]
    leaf = name.rsplit(".", 1)[-1]
    text = ev.get("message", "")
    if text.startswith(f"[{leaf}] "):
        text = text[len(leaf) + 3:]
    fsw = epoch(ev["generationTime"]) - gen_offset
    return (f"TB_PROC_TIME: {fsw:.6f}s, context=0,(rx={epoch(ev['receptionTime']):.6f}),{log_name(deployment, name).replace(',', ';')},"
            f"{int(extra.get('fprime_event_id', 0))},EventSeverity.{extra.get('fprime_severity', 'UNKNOWN')},{one_line(text)}")


def channel_name(qualified: str, root: str) -> str:
    q = qualified[len(root):] if qualified.startswith(root) else qualified
    return q.strip("/").replace("/", ".")


def channel_line(sample: dict, root: str, gen_offset: float, ids: dict, deployment: str = "") -> str:
    """`sample`: {name (qualified), generationTime, receptionTime, value}."""
    name = channel_name(sample["name"], root)
    fsw = epoch(sample["generationTime"]) - gen_offset
    value = json.dumps(sample["value"], separators=(",", ":"), sort_keys=True)
    return f"TB_PROC_TIME: {fsw:.6f}s, context=0,(rx={epoch(sample['receptionTime']):.6f}),{log_name(deployment, name)},{ids.get(name, 0)},{value}"


def parse_bridge(text: str) -> list:
    """Frames of the bench bridge log (`<UTC epoch> down <length> <first 6 bytes hex>`): TM primary header fields."""
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 4 or parts[1] != "down" or len(parts[3]) < 12:
            continue
        hdr = bytes.fromhex(parts[3][:12])
        word = (hdr[0] << 8) | hdr[1]
        rows.append({"rx": float(parts[0]), "len": int(parts[2]), "scid": (word >> 4) & 0x3FF,
                     "vcid": (word >> 1) & 0x7, "mc_count": hdr[2], "vc_count": hdr[3]})
    return rows


def merge_transfers(known: dict, listed: list, now: float) -> dict:
    """Keep one row per YAMCS transfer id; stamp the ground time it was first seen and first seen finished."""
    for t in listed:
        row = known.setdefault(str(t["id"]), {"first_seen": now, "finished_seen": None})
        row.update({k: v for k, v in t.items()})
        if row["finished_seen"] is None and t.get("state") in TERMINAL:
            row["finished_seen"] = now
    return known


def atomic_json(path: Path, data) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def channel_ids(dictionary: dict) -> dict:
    return {c["name"]: int(c["id"]) for c in dictionary.get("telemetryChannels", [])}


# ---------------------------------------------------------------- the recorder
class Recorder:
    def __init__(self, a):
        self.a = a
        self.raw = Path(a.logs)
        self.cli = self.raw / "fprime-cli-yamcs"
        self.side = self.raw / "yamcs"
        for d in (self.cli, self.side, self.raw / "files"):
            d.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.files = {n: open(p, "a", buffering=1, encoding="utf-8") for n, p in (
            ("event", self.cli / "event.log"), ("channel", self.cli / "channel.log"),
            ("events", self.side / "events.jsonl"), ("channels", self.side / "channels.jsonl"),
            ("timetags", self.side / "timetags.jsonl"), ("links", self.side / "links.jsonl"),
            ("ground", self.raw / "ground-events.log"))}
        self.transfers = {}
        self.stop = threading.Event()
        dictionary = json.loads(Path(a.dictionary).read_text(encoding="utf-8"))
        (self.raw / "dictionary.json").write_bytes(Path(a.dictionary).read_bytes())
        self.ids = channel_ids(dictionary)
        self.root = a.root.rstrip("/") + "/"

    # -- callbacks (YAMCS client threads)
    def on_event(self, event):
        ev = {"source": event.source, "type": event.event_type, "message": event.message, "severity": str(event.severity),
              "seqNumber": event.sequence_number, "generationTime": event.generation_time.isoformat(),
              "receptionTime": event.reception_time.isoformat(), "extra": dict(event.extra or {})}
        with self.lock:
            self.files["events"].write(json.dumps(ev, sort_keys=True) + "\n")
            if ev["extra"].get("fprime_event_name"):
                self.files["event"].write(event_line(ev, self.a.gen_offset, self.a.deployment) + "\n")
            else:  # a ground event (link, packet sequence): kept beside the record, not an event of the unit
                self.files["ground"].write(f"{ev['generationTime']},{ev['source']},{ev['type']},{ev['severity']},{one_line(ev['message'])}\n")

    def on_parameters(self, data):
        with self.lock:
            for p in data.parameters:
                if not p.name.startswith(self.root):
                    continue
                s = {"name": p.name, "generationTime": p.generation_time.isoformat(),
                     "receptionTime": p.reception_time.isoformat(), "value": p.eng_value}
                self.files["channels"].write(json.dumps(s, sort_keys=True, default=str) + "\n")
                self.files["channel"].write(channel_line(json.loads(json.dumps(s, default=str)), self.root,
                                                         self.a.gen_offset, self.ids, self.a.deployment) + "\n")

    def on_event_packet(self, packet):
        b = packet.binary
        if len(b) < EVENT_TIME_TAG_OFFSET + 8:
            return
        sec, usec = struct.unpack(">II", b[EVENT_TIME_TAG_OFFSET:EVENT_TIME_TAG_OFFSET + 8])
        row = {"generationTime": packet.generation_time.isoformat(), "receptionTime": packet.reception_time.isoformat(),
               "tag_seconds": sec, "tag_useconds": usec, "event_id": struct.unpack(">I", b[8:12])[0]}
        with self.lock:
            self.files["timetags"].write(json.dumps(row, sort_keys=True) + "\n")

    # -- polling (main thread)
    def get(self, path):
        import requests
        r = requests.get(f"http://{self.a.url}/api{path}", timeout=10)
        r.raise_for_status()
        return r.json()

    def poll(self, storage):
        now = time.time()
        links = self.get(f"/links/{self.a.instance}").get("links", [])
        with self.lock:
            self.files["links"].write(json.dumps({"t": now, "links": [
                {k: l.get(k) for k in ("name", "status", "dataInCount", "dataOutCount", "extra")} for l in links]}) + "\n")
        listed = self.get(f"/filetransfer/{self.a.instance}/{self.a.cfdp_service}/transfers").get("transfers", [])
        merge_transfers(self.transfers, listed, now)
        for row in self.transfers.values():
            if row.get("state") == "COMPLETED" and row.get("direction") == "DOWNLOAD" and "file" not in row:
                data = storage.download_object(row["bucket"], row["objectName"])
                name = f"{row['id']}-{Path(row['objectName']).name}"
                (self.raw / "files" / name).write_bytes(data)
                row["file"] = f"files/{name}"
                row["file_sha256"] = hashlib.sha256(data).hexdigest()
                row["file_copied"] = time.time()
        atomic_json(self.raw / "cfdp.json", {"updated": now, "transfers": sorted(self.transfers.values(), key=lambda r: int(r["id"]))})
        bridge = self.raw / "bridge.log"
        frames = parse_bridge(bridge.read_text(encoding="utf-8", errors="replace")) if bridge.is_file() else []
        tm = next((l for l in links if l.get("name") == self.a.tm_link), {})
        atomic_json(self.raw / "frames.json", {"updated": now, "source": "bench bridge log (every TM frame handed to the YAMCS TM link)",
                                               "yamcs_link": {"name": self.a.tm_link, "dataInCount": tm.get("dataInCount"), "extra": tm.get("extra")},
                                               "frames": frames})

    def run(self):
        from yamcs.client import YamcsClient
        limit = time.time() + self.a.connect_s
        while True:
            try:
                client = YamcsClient(self.a.url)
                processor = client.get_processor(self.a.instance, "realtime")
                mdb = client.get_mdb(self.a.instance)
                names = [p.qualified_name for p in mdb.list_parameters() if p.qualified_name.startswith(self.root)]
                container = next(c.qualified_name for c in mdb.list_containers() if c.qualified_name.endswith("/FPrimeEvent"))
                subs = [client.create_event_subscription(self.a.instance, self.on_event),
                        processor.create_parameter_subscription(names, on_data=self.on_parameters, abort_on_invalid=False, send_from_cache=False),
                        processor.create_container_subscription([container], on_data=self.on_event_packet)]
                break
            except Exception as exc:  # noqa: BLE001 - YAMCS is still starting
                if time.time() > limit:
                    raise SystemExit(f"recorder: YAMCS at {self.a.url} not reachable: {exc!r}")
                time.sleep(2)
        (self.cli / "recorder.ready").write_text("ready\n", encoding="utf-8")
        storage = client.get_storage_client()
        print(f"recorder: subscribed to events, {len(names)} parameters, {container}", flush=True)
        beat = 0
        while not self.stop.is_set():
            try:
                self.poll(storage)
            except Exception as exc:  # noqa: BLE001 - a poll failure is logged; the next poll retries
                print(f"recorder: poll failed: {exc!r}", flush=True)
            dead = [s for s in subs if s.done()]
            if dead:
                print(f"recorder: {len(dead)} subscription(s) closed; stopping", flush=True)
                break
            beat += 1
            if beat % 20 == 0:
                print(f"recorder: alive, transfers={len(self.transfers)}", flush=True)
            self.stop.wait(self.a.period)
        try:  # last export: what YAMCS itself archived
            self.poll(storage)
            atomic_json(self.side / "events-archive.json", self.get(f"/archive/{self.a.instance}/events?limit=100000"))
            atomic_json(self.raw / "commands.json", self.get(f"/archive/{self.a.instance}/commands?limit=100000"))
        finally:
            for s in subs:
                s.cancel()
            client.close()
            with self.lock:
                for f in self.files.values():
                    f.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", required=True)
    ap.add_argument("--instance", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--dictionary", required=True)
    ap.add_argument("--logs", required=True)
    ap.add_argument("--gen-offset", type=float, default=1.0, help="YAMCS generation time minus F Prime time tag, seconds")
    ap.add_argument("--deployment", default="", help="prefix of the names in the fth logs (subtopology dropped); empty keeps qualified names")
    ap.add_argument("--connect-s", type=float, default=180)
    ap.add_argument("--cfdp-service", default="CfdpService")
    ap.add_argument("--tm-link", default="UDP_TM_IN")
    ap.add_argument("--period", type=float, default=0.5)
    a = ap.parse_args(argv)
    rec = Recorder(a)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: rec.stop.set())
    rec.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
