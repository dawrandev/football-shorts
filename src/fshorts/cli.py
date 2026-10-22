from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from fshorts.config import AppConfig
from fshorts.evaluation import GoalDetectionEvaluator, GoalRecallEvaluator, GroundTruth
from fshorts.events import (
    AudioExcitementSource,
    CachedTranscriber,
    Candidate,
    CandidateMerger,
    CommentaryKeywordSource,
    PhraseMatcher,
    WhisperTranscriber,
)
from fshorts.ingest import AudioExtractor, FfprobeProber, FrameSampler, ProbeError, Region
from fshorts.scoreboard import (
    CachedScoreBugReader,
    EasyOcrEngine,
    GoalExtractor,
    ScoreBugParser,
    ScoreBugReader,
    ScoreTimeline,
)
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


def _cmd_goals(args: argparse.Namespace) -> int:
    config = AppConfig.load(Path(args.config))
    video = Path(args.video)
    workspace = MatchWorkspace(config.paths.outputs, video)
    board = config.scoreboard

    started = time.perf_counter()
    reader = CachedScoreBugReader(
        ScoreBugReader(FrameSampler(), EasyOcrEngine(), ScoreBugParser(board.min_confidence)),
        workspace.score_readings,
    )
    readings = reader.read(video, Region(*board.region), board.fps)
    changes = ScoreTimeline(board.confirmations).changes(readings)
    goals = GoalExtractor().goals(changes)

    workspace.goals.write_text(
        json.dumps({"changes": [c.to_dict() for c in changes], "goals": [g.to_dict() for g in goals]}, indent=1),
        encoding="utf-8",
    )
    print(f"{len(readings)} score readings, {len(changes)} changes ({time.perf_counter() - started:.0f}s)")
    for goal in goals:
        print(f"  {_format_time(goal.time)}  {goal.before[0]}-{goal.before[1]} -> {goal.after[0]}-{goal.after[1]}")
    for change in changes:
        if change.kind in ("revert", "jump"):
            print(f"  {change.kind} at {_format_time(change.time)}: {change.before} -> {change.after}")
    return 0


def _cmd_evaluate(args: argparse.Namespace) -> int:
    config = AppConfig.load(Path(args.config))
    video = Path(args.video)
    workspace = MatchWorkspace(config.paths.outputs, video)
    truth = GroundTruth.load(GROUND_TRUTH_DIR / f"{video.stem}.json")

    if workspace.candidates.is_file():
        candidates = [
            Candidate.from_dict(c) for c in json.loads(workspace.candidates.read_text(encoding="utf-8"))
        ]
        report = GoalRecallEvaluator().evaluate(truth, candidates)
        print(f"candidates: goal recall {len(report.found)}/{len(truth.goals)} "
              f"({report.recall:.0%}) with {report.candidate_count} candidates")
        for goal in report.missed:
            print(f"  missed {goal.minute}' ({goal.score_after}) at {_format_time(goal.video_time)}")

    if workspace.goals.is_file():
        detected = [g["time"] for g in json.loads(workspace.goals.read_text(encoding="utf-8"))["goals"]]
        detection = GoalDetectionEvaluator().evaluate(truth, detected)
        print(f"scoreboard: {len(detection.matched)}/{len(truth.goals)} goals, "
              f"{len(detection.false_times)} false")
        for goal in detection.missed:
            print(f"  missed {goal.minute}' ({goal.score_after}) at {_format_time(goal.video_time)}")
        for false_time in detection.false_times:
            print(f"  false goal at {_format_time(false_time)}")
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

    goals = commands.add_parser("goals", help="confirm goals from the on-screen score bug")
    goals.add_argument("video")
    goals.set_defaults(handler=_cmd_goals)

    evaluate = commands.add_parser("evaluate", help="compare candidates and goals with the ground truth")
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
