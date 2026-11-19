#!/usr/bin/env python3
"""Bench bridge between the RFM69 Feather ground radio and the fprime-yamcs UDP frame links.

The Feather exchanges F Prime frames on its USB serial port; each frame carries one radio packet. This
bridge removes that wrapper on downlink and sends the radio packet (one TM frame) as one UDP datagram to
the YAMCS TM link, and wraps each datagram of the YAMCS TC link (one TC frame) for the Feather. It does
not inspect or change the radio packets. Bench equipment: not part of the flight or ground software.
"""
import argparse
import select
import socket
import sys
import time

import serial
from fprime_gds.common.communication.framing import FpFramerDeframer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uart-device", required=True)
    parser.add_argument("--uart-baud", type=int, default=115200)
    parser.add_argument("--tm-port", type=int, required=True, help="YAMCS TM frame UDP port (downlink)")
    parser.add_argument("--tc-port", type=int, required=True, help="UDP port YAMCS sends TC frames to (uplink)")
    parser.add_argument("--log", help="append one line per radio packet to this file")
    args = parser.parse_args()

    framing = FpFramerDeframer()
    port = serial.Serial(args.uart_device, args.uart_baud, timeout=0)
    tm = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tc.bind(("127.0.0.1", args.tc_port))
    log = open(args.log, "a", buffering=1) if args.log else None
    pending = b""
    while True:
        readable, _, _ = select.select([port.fileno(), tc], [], [], 1.0)
        if port.fileno() in readable:
            pending += port.read(4096)
            while True:
                packet, pending, _ = framing.deframe(pending)
                if packet is None:
                    break
                tm.sendto(packet, ("127.0.0.1", args.tm_port))
                if log:
                    log.write(f"{time.time():.3f} down {len(packet)} {packet[:6].hex()}\n")
        if tc in readable:
            frame, _ = tc.recvfrom(4096)
            port.write(framing.frame(frame))
            if log:
                log.write(f"{time.time():.3f} up {len(frame)} {frame[:5].hex()}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
