import os
import pytest

from domains.atlas import ingestion as ing

pytestmark = pytest.mark.skipif(ing.Image is None, reason="Pillow not installed")


def _make_image(path, size=(200, 100)):
    from PIL import Image
    Image.new("RGB", size, (10, 20, 30)).save(path)


def test_import_and_select_figure(tmp_path):
    src = str(tmp_path / "fig.png")
    _make_image(src)
    doc = ing.import_document(src, str(tmp_path / "data"))
    assert os.path.isfile(doc["document_ref"])  # original preserved as copy
    crop = ing.select_figure(src, (0.0, 0.0, 0.5, 0.5), str(tmp_path / "data"),
                             document_ref=doc["document_ref"], source_page=3)
    assert (crop.image_width, crop.image_height) == (100, 50)
    assert crop.source_page == 3
    assert crop.document_ref == doc["document_ref"]


def test_bad_crop_rejected(tmp_path):
    src = str(tmp_path / "fig.png")
    _make_image(src)
    with pytest.raises(ValueError):
        ing.select_figure(src, (0.6, 0.6, 0.2, 0.2), str(tmp_path))
    with pytest.raises(NotImplementedError):
        ing.detect_figures(src)
