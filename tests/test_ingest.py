# tests/test_ingest.py
import pytest

from ingest import IngestError, ingest, parse_date

PUSH_LOG = """FitNotes Workout - Tuesday 10th November 2026
Total Volume: 1,000 Kg
Total Sets: 2
Total Reps: 16

** Incline Dumbbell Bench Press **
- 20.0 kgs x 8 reps

** Weighted Dips **
- 6 reps
"""

PULL_LOG = """FitNotes Workout - Wednesday 4th November 2026

** Lat Pulldown **
- 50.0 kgs x 8 reps
"""


@pytest.fixture
def root(tmp_path):
    (tmp_path / "push" / "2026-04-09").mkdir(parents=True)
    (tmp_path / "push" / "2026-04-09" / "log.txt").write_text(
        PUSH_LOG.replace("Tuesday 10th November", "Thursday 9th April"))
    (tmp_path / "pull" / "2026-04-10").mkdir(parents=True)
    (tmp_path / "pull" / "2026-04-10" / "log.txt").write_text(
        PULL_LOG.replace("Wednesday 4th November", "Friday 10th April"))
    for s in ("legs", "arms"):
        (tmp_path / s).mkdir()
    return tmp_path


@pytest.mark.parametrize("header,expected", [
    ("FitNotes Workout - Tuesday 10th November 2026", "2026-11-10"),
    ("FitNotes Workout - Monday 1st June 2026", "2026-06-01"),
    ("FitNotes Workout - Sunday 22nd March 2026", "2026-03-22"),
    ("FitNotes Workout - Friday 3rd April 2026", "2026-04-03"),
])
def test_parse_date(header, expected):
    assert parse_date(header) == expected


def test_parse_date_missing_header():
    with pytest.raises(IngestError):
        parse_date("** Bench Press **")


def test_infers_split_from_history(root):
    dest = ingest(PUSH_LOG, root, interactive=False)
    assert dest == root / "push" / "2026-11-10" / "log.txt"
    assert "Incline Dumbbell Bench Press" in dest.read_text()

    dest = ingest(PULL_LOG, root, interactive=False)
    assert dest == root / "pull" / "2026-11-04" / "log.txt"


def test_overwrites_empty_placeholder(root):
    (root / "push" / "2026-11-10").mkdir()
    (root / "push" / "2026-11-10" / "log.txt").write_text("")
    assert ingest(PUSH_LOG, root, interactive=False).read_text().startswith("FitNotes")


def test_refuses_to_clobber_different_log(root):
    ingest(PUSH_LOG, root, interactive=False)
    changed = PUSH_LOG.replace("8 reps", "10 reps")
    with pytest.raises(IngestError, match="already has"):
        ingest(changed, root, interactive=False)
    assert "10 reps" in ingest(changed, root, force=True, interactive=False).read_text()


def test_identical_reingest_is_noop(root):
    ingest(PUSH_LOG, root, interactive=False)
    ingest(PUSH_LOG, root, interactive=False)  # no error


def test_unknown_exercises_need_split(root):
    log = "FitNotes Workout - Monday 9th November 2026\n\n** Barbell Squat **\n- 100.0 kgs x 5 reps\n"
    with pytest.raises(IngestError, match="infer split"):
        ingest(log, root, interactive=False)
    assert ingest(log, root, split="legs").parent.parent.name == "legs"
