from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

from fshorts.broadcast import (
    BroadcastAnalyzer,
    BroadcastTimeline,
    CachedBroadcastAnalyzer,
    RecapDetector,
    ScoreBugDetector,
    SiglipViewClassifier,
)
from fshorts.clipping import ClipCutter, ClipPlanner, FfmpegSceneCutDetector, SceneSnapper
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
    Word,
)
from fshorts.events.replay_events import QwenGenerator, ReplayEvent, ReplayEventClassifier
from fshorts.ingest import AudioExtractor, FfprobeProber, FrameSampler, ProbeError, Region
from fshorts.scoreboard import (
    CachedScoreBugReader,
    EasyOcrEngine,
    GoalExtractor,
    ScoreBugParser,
    ScoreBugReader,
    ScoreChange,
    ScoreReading,
    ScoreTimeline,
)
from fshorts.reframe.balldata import BallPseudoLabeler, CocoTileWriter
from fshorts.reframe import (
    BlurFitRenderer,
    CachedDetections,
    LanczosUpscaler,
    RealEsrganUpscaler,
    CropPathPlanner,
    FrameDetections,
    RfDetrDetector,
    VerticalCropRenderer,
)
from fshorts.review import LabelStore, ReviewSession
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


def _cmd_moments(args: argparse.Namespace) -> int:
    config = AppConfig.load(Path(args.config))
    video = Path(args.video)
    workspace = MatchWorkspace(config.paths.outputs, video)
    readings = [ScoreReading.from_dict(r) for r in _load_json(workspace.score_readings, "goals")]
    words = [Word(**w) for w in _load_json(workspace.transcript, "candidates")]

    started = time.perf_counter()
    analyzer = CachedBroadcastAnalyzer(
        BroadcastAnalyzer(FrameSampler(), SiglipViewClassifier(), ScoreBugDetector()), workspace.broadcast
    )
    timeline = analyzer.analyze(video, Region(*config.scoreboard.region), readings)
    replays = timeline.replays()
    detector = RecapDetector(FrameSampler())
    recaps = detector.recaps(detector.thumbnails(video), replays)
    events = ReplayEventClassifier(QwenGenerator()).classify(replays, words)
    events = [replace(e, recap=r) for e, r in zip(events, recaps)]
    workspace.replay_events.write_text(
        json.dumps([e.to_dict() for e in events], ensure_ascii=False, indent=1), encoding="utf-8"
    )
    for event in events:
        flag = " (recap)" if event.recap else ""
        print(f"  {_format_time(event.replay.start)}  {event.kind:16} {event.player or '-'}{flag}  {event.summary}")
    print(f"{len(replays)} replays classified ({time.perf_counter() - started:.0f}s)")
    return 0


def _load_json(path: Path, step: str):
    if not path.is_file():
        raise FileNotFoundError(f"{path} missing, run 'fshorts {step}' first")
    return json.loads(path.read_text(encoding="utf-8"))


def _cmd_cut(args: argparse.Namespace) -> int:
    config = AppConfig.load(Path(args.config))
    video = Path(args.video)
    workspace = MatchWorkspace(config.paths.outputs, video)

    goals = [ScoreChange.from_dict(g) for g in _load_json(workspace.goals, "goals")["goals"]]
    readings = [ScoreReading.from_dict(r) for r in _load_json(workspace.score_readings, "goals")]
    candidates = [Candidate.from_dict(c) for c in _load_json(workspace.candidates, "candidates")]
    duration = FfprobeProber().probe(video).duration_seconds
    timeline = events = None
    if workspace.replay_events.is_file():
        timeline = BroadcastTimeline.from_dict(_load_json(workspace.broadcast, "moments"))
        events = [ReplayEvent.from_dict(e) for e in _load_json(workspace.replay_events, "moments")]

    started = time.perf_counter()
    plans = ClipPlanner(config.clip).plan(goals, readings, candidates, duration, timeline, events)
    for old in workspace.clips_dir.glob("*.mp4"):
        old.unlink()
    snapper = SceneSnapper(FfmpegSceneCutDetector(), config.clip.snap_seconds)
    cutter = ClipCutter(config.output.encoder, config.output.bitrate)

    clips = []
    for number, plan in enumerate(plans, 1):
        plan = snapper.snap(video, plan)
        clip_id = f"{number:02d}_{plan.kind}_{int(plan.anchor)}"
        cutter.cut(video, plan, workspace.clips_dir / f"{clip_id}.mp4")
        clips.append({
            "id": clip_id, "file": f"{clip_id}.mp4", "kind": plan.kind, "label": plan.label,
            "anchor": plan.anchor, "start": round(plan.start, 2), "end": round(plan.end, 2), "score": plan.score,
        })
        print(f"  {clip_id}  {_format_time(plan.start)}-{_format_time(plan.end)}  {plan.label}")

    workspace.clips.write_text(json.dumps(clips, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = Counter(c["kind"] for c in clips)
    summary = ", ".join(f"{n} {kind}" for kind, n in sorted(counts.items()))
    print(f"{summary} -> {workspace.clips_dir} ({time.perf_counter() - started:.0f}s)")
    return 0


def _cmd_vertical(args: argparse.Namespace) -> int:
    config = AppConfig.load(Path(args.config))
    out = config.output
    workspace = MatchWorkspace(config.paths.outputs, Path(args.video))
    clips = _load_json(workspace.clips, "cut")
    if args.kinds:
        clips = [c for c in clips if c["kind"] in args.kinds.split(",")]

    prober, sampler, cuts = FfprobeProber(), FrameSampler(), FfmpegSceneCutDetector()
    detector = None
    upscaler = RealEsrganUpscaler(out.sr_weights) if out.upscaler == "realesrgan" else LanczosUpscaler()
    crop = VerticalCropRenderer(sampler, upscaler, out.width, out.height, out.encoder, out.bitrate, out.layout,
                                out.window_aspect, out.zoom, out.top_margin)
    blur = BlurFitRenderer(out.width, out.height, out.encoder, out.bitrate)
    started = time.perf_counter()
    video = Path(args.video)
    match = prober.probe(video)
    size = (match.width, match.height)
    for clip in clips:
        start, end = clip["start"], clip["end"]
        target = workspace.vertical_dir / clip["file"]
        cache = CachedDetections(workspace.detections_dir / f"{clip['id']}.json")
        detections = cache.load()
        if detections is None:
            detector = detector or RfDetrDetector(ball_weights=out.ball_weights)
            samples = list(sampler.sample(video, out.detect_fps, Region(0, 0, *size), start=start,
                                          duration=end - start))
            boxes = detector.detect([frame for _, frame in samples])
            detections = [FrameDetections(t, players, balls) for (t, _), (players, balls) in zip(samples, boxes)]
            cache.save(detections)
        shot_cuts = [c - start for c in cuts.cuts(video, start, end)]
        path = CropPathPlanner(*size, out.smooth_seconds).plan(detections, shot_cuts)
        if out.layout != "blur" and path.coverage >= out.min_coverage:
            crop.render(video, start, end, path, size, match.fps, target)
            inside = path.ball_inside(crop.crop_width(match.height))
            how = (f"{out.layout}, ball seen {path.ball_coverage:.0%}"
                   + (f", in frame {inside:.0%}" if inside is not None else ""))
        else:
            blur.render(video, start, end, target)
            how = f"blur, followed {path.coverage:.0%}"
        print(f"  {clip['id']}  {how}")
    print(f"{len(clips)} vertical clips -> {workspace.vertical_dir} ({time.perf_counter() - started:.0f}s)")
    return 0


def _cmd_balldata(args: argparse.Namespace) -> int:
    """Pseudo-labelled ball tiles for training; the --test matches only go to the test split."""
    config = AppConfig.load(Path(args.config))
    writer = CocoTileWriter(Path(args.out))
    labeler = BallPseudoLabeler(FrameSampler(), RfDetrDetector())
    started = time.perf_counter()
    for video, held_out in [(Path(v), False) for v in args.videos] + [(Path(v), True) for v in args.test or []]:
        workspace = MatchWorkspace(config.paths.outputs, video)
        timeline = BroadcastTimeline.from_dict(_load_json(workspace.broadcast, "moments"))
        info = FfprobeProber().probe(video)
        windows = labeler.windows(timeline, info.duration_seconds)
        count = 0
        for number, start in enumerate(windows):
            split = "test" if held_out else ("valid" if number % 10 == 0 else "train")
            for index, (frame, label) in enumerate(labeler.label(video, start, (info.width, info.height))):
                if index % 5 == 0:   # 2 fps keeps neighbouring tiles from being near copies
                    writer.add(split, f"{video.stem}_{label.time:.1f}", frame, label)
                    count += 1
        print(f"  {video.stem}: {len(windows)} live windows, {count} labelled frames")
    print(f"{writer.close()} -> {args.out} ({time.perf_counter() - started:.0f}s)")
    return 0


def _cmd_trainball(args: argparse.Namespace) -> int:
    from rfdetr import RFDETRMedium

    RFDETRMedium(resolution=640).train(
        dataset_dir=args.data, output_dir=args.out, epochs=args.epochs, batch_size=args.batch, lr=1e-4,
    )
    print(f"ball model -> {args.out}")
    return 0


def _cmd_review(args: argparse.Namespace) -> int:
    config = AppConfig.load(Path(args.config))
    video = Path(args.video)
    workspace = MatchWorkspace(config.paths.outputs, video)
    store = LabelStore(config.paths.labels / f"{video.stem}.json")

    reviewed = ReviewSession(store).run(_load_json(workspace.clips, "cut"), workspace.clips_dir)
    print(f"{reviewed} clips reviewed, labels in {config.paths.labels / f'{video.stem}.json'}")
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

    moments = commands.add_parser("moments", help="find replays and ask a local LLM what each one shows")
    moments.add_argument("video")
    moments.set_defaults(handler=_cmd_moments)

    cut = commands.add_parser("cut", help="plan and cut 16:9 highlight clips")
    cut.add_argument("video")
    cut.set_defaults(handler=_cmd_cut)

    vertical = commands.add_parser("vertical", help="reframe cut clips to 9:16, following the action")
    vertical.add_argument("video")
    vertical.add_argument("--kinds", help="comma separated clip kinds, e.g. goal,chance")
    vertical.set_defaults(handler=_cmd_vertical)

    balldata = commands.add_parser("balldata", help="build pseudo-labelled ball tiles to train our ball detector")
    balldata.add_argument("videos", nargs="+")
    balldata.add_argument("--test", nargs="*", help="matches kept out of training, for the test split only")
    balldata.add_argument("--out", default="data/datasets/ball")
    balldata.set_defaults(handler=_cmd_balldata)

    trainball = commands.add_parser("trainball", help="fine-tune RF-DETR on the pseudo-labelled ball tiles")
    trainball.add_argument("--data", default="data/datasets/ball")
    trainball.add_argument("--out", default="models/ball")
    trainball.add_argument("--epochs", type=int, default=20)
    trainball.add_argument("--batch", type=int, default=16)
    trainball.set_defaults(handler=_cmd_trainball)

    review = commands.add_parser("review", help="accept or reject cut clips (training labels)")
    review.add_argument("video")
    review.set_defaults(handler=_cmd_review)

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
