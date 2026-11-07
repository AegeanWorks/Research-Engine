"""Frame quality: blank cards, duplicates, sharpness (my own viewing, automated)."""
import os

import pytest

from PIL import Image, ImageDraw

from domains.atlas import quality as qa


def _img(path, color, size=(160, 120), noise=False):
    from PIL import Image, ImageDraw
    import random
    img = Image.new("RGB", size, color)
    if noise:
        rnd = random.Random(7)
        draw = ImageDraw.Draw(img)
        for _ in range(400):
            x, y = rnd.randrange(size[0]), rnd.randrange(size[1])
            draw.point((x, y), fill=(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)))
    img.save(path)
    return path


def test_blank_and_duplicate_frames_filtered(tmp_path):
    blank = _img(str(tmp_path / "blank.png"), (11, 33, 77))
    dup1 = _img(str(tmp_path / "d1.png"), (200, 50, 50), noise=True)
    dup2 = _img(str(tmp_path / "d2.png"), (200, 50, 50), noise=True)
    sharp = _img(str(tmp_path / "s.png"), (10, 200, 60), noise=True)
    report = qa.frames_quality([blank, dup1, dup2, sharp])
    verdicts = {os.path.basename(f["path"]): f["verdict"] for f in report["frames"]}
    assert verdicts["blank.png"] == "blank-transition-card"
    assert verdicts["d2.png"] == "near-duplicate"
    assert verdicts["d1.png"] == "keep" and verdicts["s.png"] == "keep"
    assert report["kept"] == [1, 3]
    assert report["score"] == 50


def test_low_detail_flagged_but_kept(tmp_path):
    import random
    img = Image.new("RGB", (320, 320))
    px = img.load()
    rnd = random.Random(11)
    for y in range(320):
        for x in range(320):
            v = 120 + rnd.randint(-3, 3)
            px[x, y] = (v, v, v)
    grain = str(tmp_path / "grain.png")
    img.save(grain)
    report = qa.frames_quality([grain])
    assert report["frames"][0]["verdict"] == "low-detail"
    assert report["kept"] == [0]
    assert any("low-detail" in i for i in report["issues"])


def test_sharpness_orders_detail(tmp_path):
    flat = _img(str(tmp_path / "flat.png"), (100, 100, 100))
    busy = _img(str(tmp_path / "busy.png"), (100, 100, 100), noise=True)
    assert qa.frame_sharpness(str(busy)) > qa.frame_sharpness(str(flat))
    assert isinstance(qa.ahash(str(busy)), int) and qa.ahash(str(busy)) != 0


def test_real_mp4_frames_analyzed():
    root = __import__("pathlib").Path(__file__).resolve().parents[3]
    mp4s = sorted(__import__("glob").glob(
        "C:/Users/Yunus-Emre/Desktop/Materials/*.mp4"))  # hygiene: allow opt-in local videos, skips when absent
    mp4s += sorted(__import__("glob").glob(str(root / "Atlas" / "demo" / "*.mp4")))
    pytest.importorskip("imageio_ffmpeg")
    if not mp4s:
        pytest.skip("no real videos present")
    from domains.atlas import sources as src
    import tempfile
    frames = src.video_frames(mp4s[0], tempfile.mkdtemp(), max_frames=4)
    report = qa.frames_quality(frames)
    assert report["frames"] and any(
        f["verdict"] in ("keep", "near-duplicate", "blank-transition-card")
        for f in report["frames"])
