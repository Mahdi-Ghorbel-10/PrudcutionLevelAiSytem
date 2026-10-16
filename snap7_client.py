#!/usr/bin/env python3
"""Read and write Siemens S7 PLC data with python-snap7.

Defaults target S7-1200/1500. Set PLC_IP, PLC_RACK, PLC_SLOT, PLC_DB,
PLC_OFFSET, and PLC_VALUE through CLI arguments or environment variables.
"""

from __future__ import annotations

import argparse
import os

import sys
from typing import Final

import snap7
from snap7.util import get_bool, get_real, get_int, set_bool, set_real, set_int

DEFAULT_IP: Final = "192.168.0.1"
DEFAULT_RACK: Final = 0
DEFAULT_SLOT: Final = 1
DEFAULT_DB: Final = 1
DEFAULT_OFFSET: Final = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read/write values on an S7 PLC")
    parser.add_argument("--ip", default=os.getenv("PLC_IP", DEFAULT_IP))
    parser.add_argument("--rack", type=int, default=int(os.getenv("PLC_RACK", DEFAULT_RACK)))
    parser.add_argument("--slot", type=int, default=int(os.getenv("PLC_SLOT", DEFAULT_SLOT)))
    parser.add_argument("--db", type=int, default=int(os.getenv("PLC_DB", DEFAULT_DB)))
    parser.add_argument("--offset", type=int, default=int(os.getenv("PLC_OFFSET", DEFAULT_OFFSET)))
    parser.add_argument("--bit", type=int, help="DB bit number 0-7; read or write with --value")
    parser.add_argument("--value", type=float, help="Value to write; omit for read")
    parser.add_argument("--type", choices=("bool", "int", "real"), default="real")
    parser.add_argument("--timeout", type=int, default=3000, help="Connection timeout in milliseconds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.offset < 0 or args.db < 1:
        raise ValueError("DB must be >= 1 and offset must be >= 0")
    if args.bit is not None and not 0 <= args.bit <= 7:
        raise ValueError("bit must be between 0 and 7")
    if args.type == "bool" and args.bit is None:
        raise ValueError("--bit is required for --type bool")

    plc = snap7.Client()
    try:
        plc.connect(args.ip, args.rack, args.slot, args.timeout)
        if not plc.get_connected():
            raise ConnectionError(f"Could not connect to PLC at {args.ip}")

        size = 1 if args.type == "bool" else 2 if args.type == "int" else 4
        data = bytearray(plc.db_read(args.db, args.offset, size))

        if args.value is None:
            if args.type == "bool":
                result = get_bool(data, 0, args.bit)
            elif args.type == "int":
                result = get_int(data, 0)
            else:
                result = get_real(data, 0)
            print(result)
            return 0

        if args.type == "bool":
            set_bool(data, 0, args.bit, bool(args.value))
        elif args.type == "int":
            set_int(data, 0, int(args.value))
        else:
            set_real(data, 0, float(args.value))
        plc.db_write(args.db, args.offset, data)
        print(f"DB{args.db}.DBX{args.offset}.{args.bit} = {bool(args.value)}" if args.type == "bool" else f"DB{args.db}.DBB{args.offset} = {args.value}")
        return 0
    finally:
        plc.disconnect()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"PLC error: {error}", file=sys.stderr)
        raise SystemExit(1)
