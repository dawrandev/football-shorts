from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fshorts.ingest import FfprobeProber, ProbeError


def _cmd_probe(args: argparse.Namespace) -> int:
    info = FfprobeProber().probe(Path(args.video))
    print(f"file:      {info.path}")
    print(f"duration:  {info.duration_label} ({info.duration_seconds:.1f}s)")
    print(f"size:      {info.width}x{info.height}")
    print(f"fps:       {info.fps:.2f}")
    print(f"codec:     {info.video_codec}")
    print(f"audio:     {'yes' if info.has_audio else 'no'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fshorts")
    commands = parser.add_subparsers(dest="command", required=True)

    probe = commands.add_parser("probe", help="show video metadata")
    probe.add_argument("video")
    probe.set_defaults(handler=_cmd_probe)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except ProbeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
