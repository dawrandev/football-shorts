import numpy as np
import pytest

from fshorts.reframe import CropPathPlanner, FrameDetections

W, H = 1920, 1080


def player(x, height=80, score=0.9):
    return [x - 15, 500, x + 15, 500 + height, score]


def frame(t, players=(), balls=()):
    return FrameDetections(t, np.array(players, np.float32).reshape(-1, 5), np.array(balls, np.float32).reshape(-1, 5))


def ball(x, score=0.8):
    return [x - 6, 600, x + 6, 612, score]


def test_follows_ball_blended_with_players():
    detections = [frame(t / 10, [player(1000), player(1100)], [ball(1400)]) for t in range(30)]

    path = CropPathPlanner(W, H, smooth_seconds=0).plan(detections, [])

    # players nearer the previous focus weigh more, so the crowd part leans slightly to 1100
    assert path.center(1.0) == pytest.approx(0.75 * 1400 + 0.25 * 1050, abs=5)
    assert path.coverage == 1.0


def test_gaps_are_interpolated_and_unreliable_balls_ignored():
    detections = [frame(0.0, [player(400)]), frame(0.5, [], [ball(900, score=0.2)]), frame(1.0, [player(800)])]

    path = CropPathPlanner(W, H, smooth_seconds=0).plan(detections, [])

    assert path.center(0.5) == pytest.approx(600)
    assert path.coverage == pytest.approx(2 / 3)


def test_close_up_frames_the_big_person():
    detections = [frame(t / 10, [player(300), player(1500, height=700)]) for t in range(10)]

    path = CropPathPlanner(W, H, smooth_seconds=0).plan(detections, [])

    assert path.center(0.5) == pytest.approx(1500)


def test_camera_cut_jumps_without_blending():
    detections = [frame(t / 10, [player(400)]) for t in range(20)] + \
                 [frame(2 + t / 10, [player(1500)]) for t in range(20)]

    path = CropPathPlanner(W, H, smooth_seconds=0.6).plan(detections, [1.95])

    assert len(path.segments) == 2
    assert path.center(1.9) == pytest.approx(400, abs=1)
    assert path.center(1.96) == pytest.approx(1500, abs=1)
