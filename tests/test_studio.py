import json
import threading
import urllib.request

import pytest

from fshorts.studio.ratings import RatingStore, ShortRating
from fshorts.studio.server import serve


@pytest.fixture
def studio(tmp_path):
    match = tmp_path / "outputs" / "m1"
    (match / "shorts").mkdir(parents=True)
    (match / "shorts" / "01_goal_100.mp4").write_bytes(bytes(range(256)) * 40)
    (match / "shorts.json").write_text(json.dumps([{"id": "01_goal_100", "file": "01_goal_100.mp4", "kind": "goal",
                                                    "label": "1-0", "start": 88.0, "end": 104.0, "anchor": 100.0,
                                                    "title": "Wow BRA vs KOR", "hook": "Watch this 🔥"}]))
    server = serve(tmp_path / "outputs", tmp_path / "labels", "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}", tmp_path
    server.shutdown()


def post(url, body):
    request = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return urllib.request.urlopen(request)


def test_queue_lists_shorts_and_rating_is_saved(studio):
    base, root = studio
    items = json.loads(urllib.request.urlopen(base + "/api/queue").read())["items"]
    assert [(i["id"], i["rating"]) for i in items] == [("01_goal_100", None)]

    post(base + "/api/rate", {"match": "m1", "id": "01_goal_100", "stars": 4, "reasons": ["good_cut"], "note": "ok"})

    saved = RatingStore(root / "labels").load("m1")["01_goal_100"]
    assert (saved.stars, saved.reasons, saved.start, saved.kind) == (4, ("good_cut",), 88.0, "goal")
    assert json.loads(urllib.request.urlopen(base + "/api/queue").read())["items"][0]["rating"]["stars"] == 4


def test_video_supports_byte_ranges(studio):
    base, _ = studio
    request = urllib.request.Request(base + "/video/m1/01_goal_100.mp4", headers={"Range": "bytes=10-19"})
    response = urllib.request.urlopen(request)
    assert response.status == 206 and response.read() == bytes(range(10, 20))


def test_bad_rating_and_path_tricks_are_refused(studio):
    base, _ = studio
    with pytest.raises(urllib.error.HTTPError) as error:
        post(base + "/api/rate", {"match": "m1", "id": "01_goal_100", "stars": 9})
    assert error.value.code == 400
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(base + "/video/..%2F..%2Fsecret/x.mp4")
    assert error.value.code == 404


def test_rating_validation():
    with pytest.raises(ValueError):
        ShortRating("x", 3, ("made_up",))
