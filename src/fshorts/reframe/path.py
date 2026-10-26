from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy.ndimage import gaussian_filter1d

from fshorts.reframe.detection import FrameDetections

# A person this tall (share of frame height) means a close-up: frame the person, not the pitch
CLOSE_UP_HEIGHT = 0.45
# Smaller boxes are crowd or far-away noise
MIN_PLAYER_HEIGHT = 0.03
BALL_START_SCORE = 0.5     # a new ball track needs a confident detection
BALL_KEEP_SCORE = 0.25     # weaker ones are accepted only where the track expects the ball
BALL_GATE = 0.08           # search radius around the predicted ball (share of width) ...
BALL_COAST_SECONDS = 0.6   # ... kept for this long without a match before the track is dropped
BALL_MAX_SIZE = 0.04       # share of frame width; anything larger is not the ball
BALL_WEIGHT = 0.75         # blend of ball and player focus when both are seen
FOLLOW_WIDTH = 0.25        # players near the previous focus (share of width) count most
# Without the ball, trust the TV camera operator: they keep the ball near the middle of the frame
CAMERA_PRIOR = 0.5


class BallTracker:
    """Picks the real ball among the candidates of each frame with a constant-velocity gate.

    Tiles find the ball in most frames but also gloves, heads and boots; a confident detection
    starts a track, and after that only candidates near where the ball should be are taken.
    """

    def __init__(self, frame_width: int) -> None:
        self._width = frame_width
        self._position: np.ndarray | None = None
        self._velocity = np.zeros(2)
        self._seen = 0.0

    def update(self, time: float, balls: np.ndarray) -> float | None:
        size = np.maximum(balls[:, 2] - balls[:, 0], balls[:, 3] - balls[:, 1])
        balls = balls[size <= BALL_MAX_SIZE * self._width]
        centers = np.column_stack([(balls[:, 0] + balls[:, 2]) / 2, (balls[:, 1] + balls[:, 3]) / 2])
        scores = balls[:, 4]
        if self._position is not None and time - self._seen > BALL_COAST_SECONDS:
            self._position = None
        if self._position is not None:
            dt = time - self._seen
            expected = self._position + self._velocity * dt
            radius = BALL_GATE * self._width + np.linalg.norm(self._velocity) * dt * 0.5
            distance = np.linalg.norm(centers - expected, axis=1) if len(centers) else np.zeros(0)
            near = (distance <= radius) & (scores >= BALL_KEEP_SCORE)
            if near.any():
                best = np.flatnonzero(near)[np.argmax(scores[near] - 0.3 * distance[near] / radius)]
                self._velocity = 0.5 * self._velocity + 0.5 * (centers[best] - self._position) / max(dt, 1e-3)
                return self._accept(time, centers[best])
            return None
        if len(scores) and scores.max() >= BALL_START_SCORE:
            self._velocity = np.zeros(2)
            return self._accept(time, centers[scores.argmax()])
        return None

    def _accept(self, time: float, center: np.ndarray) -> float:
        self._position, self._seen = center, time
        return float(center[0])


@dataclass(frozen=True)
class PathSegment:
    """Crop centre over one camera shot."""

    times: np.ndarray
    centers: np.ndarray
    end: float = float("inf")   # the camera cut that ends the shot
    balls: np.ndarray | None = None   # tracked ball x per sample, NaN where it was not found


@dataclass(frozen=True)
class CropPath:
    segments: tuple[PathSegment, ...]
    coverage: float            # share of samples where the focus was found, not guessed

    def ball_inside(self, crop_width: float) -> float | None:
        """Share of tracked-ball samples that the moving window actually shows."""
        inside = total = 0
        for segment in self.segments:
            seen = ~np.isnan(segment.balls)
            total += seen.sum()
            inside += (np.abs(segment.balls[seen] - segment.centers[seen]) <= crop_width / 2).sum()
        return inside / total if total else None

    @property
    def ball_coverage(self) -> float:
        samples = sum(len(s.times) for s in self.segments)
        return sum(int((~np.isnan(s.balls)).sum()) for s in self.segments) / samples

    def center(self, time: float) -> float:
        for segment in self.segments:
            if time < segment.end:
                return float(np.interp(time, segment.times, segment.centers))
        raise ValueError("empty path")


class CropPathPlanner:
    """Where the 9:16 window looks: the ball when the detector sees it, else the players around the play.

    Each camera shot is smoothed on its own (offline, so the window moves before the ball does not
    lag), and a cut jumps straight to the new framing like a human editor would.
    """

    def __init__(self, frame_width: int, frame_height: int, smooth_seconds: float = 0.6) -> None:
        self._width = frame_width
        self._height = frame_height
        self._smooth = smooth_seconds

    def plan(self, detections: list[FrameDetections], cuts: list[float]) -> CropPath:
        if not detections:
            raise ValueError("no detections")
        segments, found = [], 0
        chunks = self._split(detections, cuts)
        for index, chunk in enumerate(chunks):
            raw, previous, tracker, seen = [], None, BallTracker(self._width), []
            for frame in chunk:
                focus = self._focus(frame, previous, tracker, seen)
                raw.append(focus)
                previous = focus if focus is not None else previous
            found += sum(f is not None for f in raw)
            end = self._cut_before(chunks[index + 1][0].time, cuts) if index + 1 < len(chunks) else float("inf")
            segments.append(replace(self._smoothed(chunk, raw, end), balls=np.array(seen, dtype=np.float64)))
        return CropPath(tuple(segments), found / len(detections))

    @staticmethod
    def _split(detections: list[FrameDetections], cuts: list[float]) -> list[list[FrameDetections]]:
        chunks, current, pending = [], [], sorted(cuts)
        for frame in detections:
            if pending and frame.time >= pending[0] and current:
                chunks.append(current)
                current = []
            while pending and frame.time >= pending[0]:
                pending.pop(0)
            current.append(frame)
        return chunks + [current]

    @staticmethod
    def _cut_before(time: float, cuts: list[float]) -> float:
        return max((c for c in cuts if c <= time), default=time)

    def _focus(
        self, frame: FrameDetections, previous: float | None, tracker: BallTracker, seen: list[float]
    ) -> float | None:
        players = frame.players[(frame.players[:, 3] - frame.players[:, 1]) >= MIN_PLAYER_HEIGHT * self._height]
        heights = players[:, 3] - players[:, 1]
        ball_x = tracker.update(frame.time, frame.balls)
        seen.append(np.nan if ball_x is None else ball_x)
        if len(players) and heights.max() >= CLOSE_UP_HEIGHT * self._height:
            big = players[heights.argmax()]
            return float((big[0] + big[2]) / 2)
        crowd_x = self._players_focus(players, previous)
        if ball_x is not None:
            return ball_x if crowd_x is None else BALL_WEIGHT * ball_x + (1 - BALL_WEIGHT) * crowd_x
        if crowd_x is None:
            return None
        return CAMERA_PRIOR * self._width / 2 + (1 - CAMERA_PRIOR) * crowd_x

    def _players_focus(self, players: np.ndarray, previous: float | None) -> float | None:
        if not len(players):
            return None
        centers = (players[:, 0] + players[:, 2]) / 2
        if previous is None:
            return float(np.median(centers))
        weights = players[:, 4] * np.exp(-(((centers - previous) / (FOLLOW_WIDTH * self._width)) ** 2))
        if weights.sum() < 1e-3:
            return float(np.median(centers))
        return float((centers * weights).sum() / weights.sum())

    def _smoothed(self, chunk: list[FrameDetections], raw: list[float | None], end: float) -> PathSegment:
        times = np.array([f.time for f in chunk], dtype=np.float64)
        known = np.array([r is not None for r in raw])
        if known.any():
            values = np.interp(times, times[known], np.array([r for r in raw if r is not None]))
        else:
            values = np.full(len(times), self._width / 2)
        step = np.median(np.diff(times)) if len(times) > 1 else 1.0
        sigma = self._smooth / step
        if len(values) > 2 and sigma > 0:
            values = gaussian_filter1d(values, sigma, mode="nearest")
        return PathSegment(times, values, end)
