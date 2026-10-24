from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter1d

from fshorts.reframe.detection import FrameDetections

# A person this tall (share of frame height) means a close-up: frame the person, not the pitch
CLOSE_UP_HEIGHT = 0.45
# Smaller boxes are crowd or far-away noise
MIN_PLAYER_HEIGHT = 0.03
BALL_MIN_SCORE = 0.4
BALL_MAX_SIZE = 0.04       # share of frame width; anything larger is not the ball
BALL_WEIGHT = 0.75         # blend of ball and player focus when both are seen
FOLLOW_WIDTH = 0.25        # players near the previous focus (share of width) count most


@dataclass(frozen=True)
class PathSegment:
    """Crop centre over one camera shot."""

    times: np.ndarray
    centers: np.ndarray
    end: float = float("inf")   # the camera cut that ends the shot


@dataclass(frozen=True)
class CropPath:
    segments: tuple[PathSegment, ...]
    coverage: float            # share of samples where the focus was found, not guessed

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
            raw, previous = [], None
            for frame in chunk:
                focus = self._focus(frame, previous)
                raw.append(focus)
                previous = focus if focus is not None else previous
            found += sum(f is not None for f in raw)
            end = self._cut_before(chunks[index + 1][0].time, cuts) if index + 1 < len(chunks) else float("inf")
            segments.append(self._smoothed(chunk, raw, end))
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

    def _focus(self, frame: FrameDetections, previous: float | None) -> float | None:
        players = frame.players[(frame.players[:, 3] - frame.players[:, 1]) >= MIN_PLAYER_HEIGHT * self._height]
        heights = players[:, 3] - players[:, 1]
        if len(players) and heights.max() >= CLOSE_UP_HEIGHT * self._height:
            big = players[heights.argmax()]
            return float((big[0] + big[2]) / 2)
        crowd_x = self._players_focus(players, previous)
        ball_x = self._ball_focus(frame.balls, previous if previous is not None else crowd_x)
        if ball_x is not None and crowd_x is not None:
            return BALL_WEIGHT * ball_x + (1 - BALL_WEIGHT) * crowd_x
        return ball_x if ball_x is not None else crowd_x

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

    def _ball_focus(self, balls: np.ndarray, near: float | None) -> float | None:
        size = np.maximum(balls[:, 2] - balls[:, 0], balls[:, 3] - balls[:, 1])
        balls = balls[(balls[:, 4] >= BALL_MIN_SCORE) & (size <= BALL_MAX_SIZE * self._width)]
        if not len(balls):
            return None
        centers = (balls[:, 0] + balls[:, 2]) / 2
        best = np.abs(centers - near).argmin() if near is not None else balls[:, 4].argmax()
        return float(centers[best])

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
