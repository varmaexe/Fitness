# tests/test_tracking.py
import subprocess

import pytest

import bot
from trainer.tracking import git_commit, restore, snapshot, weight_trend


def _w(root, day, kg):
    (root / "weight").mkdir(exist_ok=True)
    (root / "weight" / f"{day}.txt").write_text(f"{kg}kg\n")


def test_weight_trend_needs_two_weighins(tmp_path):
    _w(tmp_path, "2026-11-13", 80)
    assert weight_trend(tmp_path, "2026-11-13") is None


def test_weight_trend_this_week_only(tmp_path):
    _w(tmp_path, "2026-11-12", 80.0)
    _w(tmp_path, "2026-11-13", 80.4)
    assert weight_trend(tmp_path, "2026-11-13") == "7-day avg 80.2 kg (2 weigh-ins)"


def test_weight_trend_vs_prior_week(tmp_path):
    for d, kg in [("2026-11-01", 81), ("2026-11-03", 81), ("2026-11-12", 80.5), ("2026-11-13", 80.3)]:
        _w(tmp_path, d, kg)
    assert weight_trend(tmp_path, "2026-11-13") == "7-day avg 80.4 kg (−0.6 vs prior week)"


def test_snapshot_restore(tmp_path):
    old = tmp_path / "sleep" / "2026-11-13.txt"
    old.parent.mkdir()
    old.write_text("before")
    new = tmp_path / "push" / "2026-11-13" / "log.txt"
    snap = snapshot(tmp_path, [old, new])
    old.write_text("after")
    new.parent.mkdir(parents=True)
    new.write_text("workout")
    restore(tmp_path, snap)
    assert old.read_text() == "before"
    assert not new.exists() and not new.parent.exists()  # empty date folder removed too


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "config.json").write_text("{}")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def test_git_commit_only_given_paths(repo):
    (repo / "config.json").write_text('{"x": 1}')  # unrelated edit must stay uncommitted
    f = repo / "weight" / "2026-11-13.txt"
    f.parent.mkdir()
    f.write_text("80kg\n")
    assert git_commit(repo, [f], "log(weight): 2026-11-13")
    assert _git(repo, "show", "--name-only", "--format=", "HEAD").split() == ["weight/2026-11-13.txt"]
    assert "config.json" in _git(repo, "status", "--porcelain")
    assert not git_commit(repo, [f], "again")  # unchanged → no commit


def test_git_commit_skips_never_committed_deleted_file(repo):
    assert not git_commit(repo, [repo / "gone.txt"], "undo")


def test_parse_schedule():
    days, at = bot.parse_schedule("", "09:00")
    assert days == tuple(range(7)) and (at.hour, at.minute) == (9, 0) and at.tzinfo
    days, at = bot.parse_schedule("sun 20:30", "x")
    assert days == (0,) and (at.hour, at.minute) == (20, 30)
    assert bot.parse_schedule("off", "09:00") is None
    with pytest.raises(KeyError):
        bot.parse_schedule("someday 10:00", "x")
