from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from fshorts.config import AppConfig
from fshorts.evaluation import GoalRecallEvaluator, GroundTruth
from fshorts.events import (
    AudioExcitementSource,
    CachedTranscriber,
    Candidate,
    CandidateMerger,
    CommentaryKeywordSource,
    PhraseMatcher,
    WhisperTranscriber,
)
from fshorts.ingest import AudioExtractor, FfprobeProber, ProbeError
from fshorts.workspace import MatchWorkspace

DEFAULT_CONFIG = Path("config.yaml")
GROUND_TRUTH_DIR = Path("tests/ground_truth")


def _format_time(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def _cmd_probe(args: argparse.Namespace) -> int:
    info = FfprobeProber().probe(Path(args.video))
    print(f"file:      {info.path}")
    print(f"duration:  {info.duration_label} ({info.duration_seconds:.1f}s)")
    print(f"size:      {info.width}x{info.height}")
    print(f"fps:       {info.fps:.2f}")
    print(f"codec:     {info.video_codec}")
    print(f"audio:     {'yes' if info.has_audio else 'no'}")
    return 0


def _cmd_candidates(args: argparse.Namespace) -> int:
    config = AppConfig.load(Path(args.config))
    video = Path(args.video)
    workspace = MatchWorkspace(config.paths.outputs, video)
    events = config.events

    started = time.perf_counter()
    audio = AudioExtractor().extract(video, workspace.audio)
    sources = [
        AudioExcitementSource(events.audio),
        CommentaryKeywordSource(
            CachedTranscriber(WhisperTranscriber(events.commentary), workspace.transcript),
            PhraseMatcher(events.commentary.phrases),
        ),
    ]
    raw: list[Candidate] = []
    for source in sources:
        found = source.detect(audio)
        print(f"{source.name:<11} {len(found)} raw candidates")
        raw.extend(found)

    merged = CandidateMerger(events.merge_seconds, events.max_candidates).merge(raw)
    workspace.candidates.write_text(
        json.dumps([c.to_dict() for c in merged], ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"{len(merged)} candidates -> {workspace.candidates} ({time.perf_counter() - started:.0f}s)")
    return 0


def _cmd_evaluate(args: argparse.Namespace) -> int:
    config = AppConfig.load(Path(args.config))
    video = Path(args.video)
    workspace = MatchWorkspace(config.paths.outputs, video)
    truth = GroundTruth.load(GROUND_TRUTH_DIR / f"{video.stem}.json")
    candidates = [
        Candidate.from_dict(c) for c in json.loads(workspace.candidates.read_text(encoding="utf-8"))
    ]

    report = GoalRecallEvaluator().evaluate(truth, candidates)
    print(f"goal recall: {len(report.found)}/{len(report.found) + len(report.missed)} "
          f"({report.recall:.0%}) with {report.candidate_count} candidates")
    for goal in report.missed:
        print(f"  missed {goal.minute}' ({goal.score_after}) at {_format_time(goal.video_time)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fshorts")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    commands = parser.add_subparsers(dest="command", required=True)

    probe = commands.add_parser("probe", help="show video metadata")
    probe.add_argument("video")
    probe.set_defaults(handler=_cmd_probe)

    candidates = commands.add_parser("candidates", help="find candidate moments from audio and commentary")
    candidates.add_argument("video")
    candidates.set_defaults(handler=_cmd_candidates)

    evaluate = commands.add_parser("evaluate", help="compare candidates with the ground truth goals")
    evaluate.add_argument("video")
    evaluate.set_defaults(handler=_cmd_evaluate)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ProbeError, FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
