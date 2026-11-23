#!/usr/bin/env python3
"""Bench bridge between the TCP connection of the PiSensor deployment and the fprime-yamcs UDP frame links.

The deployment (Drv.TcpClient) connects to this bridge. Downlink is a byte stream of TM frames of one fixed
size: the bridge cuts it into frames and sends each as one UDP datagram to the YAMCS TM link. Each datagram
of the YAMCS TC link (one TC frame) is written to the connection as it is. The bridge does not change the
frames; it writes the same log as ground/feather_bridge.py did (one line per frame), which the recorder
turns into frames.json. Bench equipment: not part of the flight or ground software.
"""
import argparse
import select
import socket
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tcp-address", default="0.0.0.0", help="address to listen on for the deployment")
    parser.add_argument("--tcp-port", type=int, required=True, help="TCP port the deployment connects to")
    parser.add_argument("--tm-frame-size", type=int, default=255, help="bytes of one TM transfer frame")
    parser.add_argument("--tm-port", type=int, required=True, help="YAMCS TM frame UDP port (downlink)")
    parser.add_argument("--tc-port", type=int, required=True, help="UDP port YAMCS sends TC frames to (uplink)")
    parser.add_argument("--log", help="append one line per frame to this file")
    args = parser.parse_args()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.tcp_address, args.tcp_port))
    server.listen(1)
    tm = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tc.bind(("127.0.0.1", args.tc_port))
    log = open(args.log, "a", buffering=1) if args.log else None

    def note(text):
        if log:
            log.write(f"{time.time():.3f} {text}\n")

    link, pending, header = None, b"", None
    while True:
        readable, _, _ = select.select([server, tc] + ([link] if link else []), [], [], 1.0)
        if server in readable:
            new, peer = server.accept()
            if link:  # one deployment: the newer connection replaces the older
                link.close()
            link, pending = new, b""
            link.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            note(f"connected {peer[0]}:{peer[1]}")
        if link and link in readable:
            try:
                data = link.recv(65536)
            except OSError:
                data = b""
            if not data:
                note(f"disconnected, {len(pending)} bytes of a frame dropped")
                link.close()
                link, pending = None, b""
            pending += data
            while link and len(pending) >= args.tm_frame_size:
                frame, pending = pending[:args.tm_frame_size], pending[args.tm_frame_size:]
                # Version and spacecraft id open every TM frame: a stream that lost its frame boundary is
                # closed (the deployment connects again and starts with a whole frame), never guessed at
                if header is None:
                    header = (frame[0], frame[1] >> 4)
                if (frame[0], frame[1] >> 4) != header:
                    note(f"desync {frame[:6].hex()}: connection closed")
                    link.close()
                    link, pending = None, b""
                    break
                tm.sendto(frame, ("127.0.0.1", args.tm_port))
                note(f"down {len(frame)} {frame[:6].hex()}")
        if tc in readable:
            frame, _ = tc.recvfrom(4096)
            if link:
                try:
                    link.sendall(frame)
                    note(f"up {len(frame)} {frame[:5].hex()}")
                except OSError:
                    note(f"up-failed {len(frame)} {frame[:5].hex()}")
            else:
                note(f"up-dropped {len(frame)} {frame[:5].hex()}: no connection")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
