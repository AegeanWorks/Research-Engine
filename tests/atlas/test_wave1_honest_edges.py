"""Wave-1 honest-error edges: non-dict entities and wrong-type podcast payloads.

Failing-first repros for audit Wave 1 (commits c7aaf42..f918684 scope):
- from_dict with non-dict entity must raise ValueError (honest 400), never AttributeError (500).
- coerce_muse_payload with non-dict entity must raise ValueError, never AttributeError.
- quality_report with JSON string parsing to non-dict must score 0 with
  podcast-parseable issue, never crash.
"""

from domains.atlas.schema import VisualAnalysis, coerce_muse_payload
from domains.atlas import quality


def test_from_dict_non_dict_entity_raises_valueerror():
    try:
        VisualAnalysis.from_dict({"entities": [42], "relationships": []})
    except ValueError:
        return
    except AttributeError as exc:
        raise AssertionError(f"AttributeError leaked instead of ValueError: {exc}")
    raise AssertionError("expected ValueError for non-dict entity")


def test_coerce_non_dict_entity_raises_valueerror():
    try:
        coerce_muse_payload({"entities": [42], "relationships": []})
    except ValueError:
        return
    except AttributeError as exc:
        raise AssertionError(f"AttributeError leaked instead of ValueError: {exc}")
    raise AssertionError("expected ValueError for non-dict muse entity")


def test_quality_wrong_type_podcast_scores_zero():
    report = quality.quality_report(
        {"entities": [], "relationships": []}, {"podcast": "[1,2]"})
    assert report["podcast"]["score"] == 0
    assert any("parseable" in c["name"] for c in report["podcast"]["checks"])
