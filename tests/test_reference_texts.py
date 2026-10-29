import numpy as np

from fshorts.references.texts import TextBox, brightness, has_emoji, join_lines, overlays, track


def box(time, text, x0=0.3, y0=0.6, x1=0.7, y1=0.63, white=0.2, emoji=False):
    return TextBox(time, x0, y0, x1, y1, text, 0.9, white, emoji)


def frames(*per_frame):
    return [list(lines) for lines in per_frame]


def test_words_of_one_row_become_one_line():
    words = [box(1.0, "goal-kick", x0=0.5, x1=0.7), box(1.0, "Kane's", x0=0.3, x1=0.48),
             box(1.0, "LALIGA", y0=0.95, y1=0.97)]

    lines = join_lines(words)

    assert [l.text for l in lines] == ["Kane's goal-kick", "LALIGA"]


def test_static_caption_is_kept_and_moving_board_dropped():
    steps = [i * 0.25 for i in range(12)]
    seen = frames(*[[box(t, "Iconic."), box(t, "FedEx", x0=0.1 + t / 10, x1=0.3 + t / 10, y0=0.3, y1=0.33)]
                    for t in steps])

    found = overlays(track(seen), duration=3.0, step=0.25)

    assert [(o.text, o.role) for o in found] == [("Iconic.", "caption")]
    assert found[0].start == 0.0 and found[0].end == 3.0
    assert found[0].y == 0.615


def test_two_beat_caption_gives_two_tracks():
    seen = frames(*[[box(i * 0.25, "Try to take the ball off him")] for i in range(8)],
                  *[[box(2 + i * 0.25, "Impossible")] for i in range(8)])

    found = overlays(track(seen), duration=4.0, step=0.25)

    assert [(o.text, o.start) for o in found] == [("Try to take the ball off him", 0.0), ("Impossible", 2.0)]


def test_short_ocr_dropout_does_not_split_a_caption():
    seen = frames(*[[box(i * 0.25, "Harry Kane's goal-kick")] for i in range(10)], [], [], [],
                  *[[box(3.25 + i * 0.25, "Harry Kane'sgoal-kick")] for i in range(10)])

    found = overlays(track(seen), duration=6.0, step=0.25)

    assert len(found) == 1 and found[0].end == 5.75


def test_corner_text_all_along_is_a_logo_and_score_is_a_bug():
    seen = frames(*[[box(i * 0.25, "LALIGA", y0=0.95, y1=0.97), box(i * 0.25, "87:10 SAB 1-0 SLA", y0=0.02, y1=0.05)]
                    for i in range(20)])

    roles = {o.text: o.role for o in overlays(track(seen), duration=5.0, step=0.25)}

    assert roles == {"LALIGA": "logo", "87:10 SAB 1-0 SLA": "scorebug"}


def test_dark_static_text_is_not_a_caption():
    seen = frames(*[[box(i * 0.25, "ULTRAS", white=0.0)] for i in range(12)])

    assert overlays(track(seen), duration=3.0, step=0.25) == []


def test_pixel_measures():
    white = np.full((10, 10, 3), 255, np.uint8)
    yellow = np.zeros((10, 10, 3), np.uint8)
    yellow[..., 0], yellow[..., 1] = 250, 200
    grass = np.zeros((10, 10, 3), np.uint8)
    grass[..., 1] = 160

    assert brightness(white) == 1.0 and brightness(grass) == 0.0
    assert has_emoji(yellow) and not has_emoji(grass) and not has_emoji(white)
