# generate_folders.py Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI script that generates consecutive YYYY-MM-DD date folders (with empty log.txt) inside a given workout target directory, starting from today and going forward.

**Architecture:** Single standalone script `generate_folders.py` at the project root. Uses `FOLDER_MAP` from `trainer/context.py` to resolve session-type aliases to actual folder names. Accepts a positional `target` arg and optional `--count` flag.

**Tech Stack:** Python 3.10+ stdlib only — `argparse`, `datetime`, `pathlib`

---

### Task 1: Write failing tests for argument parsing

**Files:**
- Create: `tests/test_generate_folders.py`

- [ ] **Step 1: Create the test file**

```python
# tests/test_generate_folders.py
import pytest
from unittest.mock import patch
from pathlib import Path


def test_imports():
    """Script can be imported without side effects."""
    import generate_folders  # noqa
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/saiverma/Development/Fitness && python -m pytest tests/test_generate_folders.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'generate_folders'`

---

### Task 2: Scaffold generate_folders.py with argument parsing

**Files:**
- Create: `generate_folders.py`

- [ ] **Step 1: Write the failing test for arg parsing**

Add to `tests/test_generate_folders.py`:

```python
import sys
from unittest.mock import patch


def test_parse_args_target_only():
    with patch("sys.argv", ["generate_folders.py", "push"]):
        import generate_folders
        args = generate_folders.parse_args()
    assert args.target == "push"
    assert args.count == 10


def test_parse_args_with_count():
    with patch("sys.argv", ["generate_folders.py", "cardio", "--count", "5"]):
        import generate_folders
        args = generate_folders.parse_args()
    assert args.target == "cardio"
    assert args.count == 5
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_generate_folders.py::test_parse_args_target_only -v
```

Expected: `FAILED` — `ModuleNotFoundError`

- [ ] **Step 3: Implement generate_folders.py with parse_args**

```python
#!/usr/bin/env python3
# generate_folders.py
"""
Generate consecutive date folders (YYYY-MM-DD) with empty log.txt files.

Usage:
    python generate_folders.py push
    python generate_folders.py cardio --count 5
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

from trainer.context import FOLDER_MAP

ROOT = Path(__file__).parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate date folders with empty log.txt files."
    )
    parser.add_argument(
        "target",
        help=f"Workout type. Valid: {', '.join(FOLDER_MAP.keys())}",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of folders to create (1–10, default: 10)",
    )
    return parser.parse_args()
```

- [ ] **Step 4: Run tests to confirm passing**

```bash
python -m pytest tests/test_generate_folders.py -v
```

Expected: All tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add generate_folders.py tests/test_generate_folders.py
git commit -m "feat: scaffold generate_folders.py with arg parsing"
```

---

### Task 3: Add target validation

**Files:**
- Modify: `generate_folders.py`
- Modify: `tests/test_generate_folders.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_generate_folders.py`:

```python
def test_validate_target_valid():
    from generate_folders import validate_target
    # Should not raise
    validate_target("push")
    validate_target("cardio")
    validate_target("sleep")


def test_validate_target_invalid():
    from generate_folders import validate_target
    with pytest.raises(SystemExit) as exc_info:
        validate_target("deadlift")
    assert exc_info.value.code != 0


def test_validate_count_valid():
    from generate_folders import validate_count
    validate_count(1)
    validate_count(10)


def test_validate_count_invalid_zero():
    from generate_folders import validate_count
    with pytest.raises(SystemExit):
        validate_count(0)


def test_validate_count_invalid_over():
    from generate_folders import validate_count
    with pytest.raises(SystemExit):
        validate_count(11)
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_generate_folders.py::test_validate_target_invalid -v
```

Expected: `FAILED` — `ImportError: cannot import name 'validate_target'`

- [ ] **Step 3: Implement validate_target and validate_count**

Add to `generate_folders.py` (after `parse_args`):

```python
def validate_target(target: str) -> None:
    if target not in FOLDER_MAP:
        valid = ", ".join(FOLDER_MAP.keys())
        print(f"Error: unknown target '{target}'. Valid options: {valid}")
        raise SystemExit(1)


def validate_count(count: int) -> None:
    if not (1 <= count <= 10):
        print(f"Error: --count must be between 1 and 10, got {count}")
        raise SystemExit(1)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_generate_folders.py -v
```

Expected: All tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add generate_folders.py tests/test_generate_folders.py
git commit -m "feat: add target and count validation to generate_folders"
```

---

### Task 4: Implement folder generation logic

**Files:**
- Modify: `generate_folders.py`
- Modify: `tests/test_generate_folders.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_generate_folders.py`:

```python
import tempfile
from datetime import date


def test_generate_folders_creates_dirs(tmp_path):
    from generate_folders import generate_folders
    target_dir = tmp_path / "push"
    target_dir.mkdir()

    today = date(2026, 4, 10)
    created, skipped = generate_folders(target_dir, today, count=3)

    assert created == 3
    assert skipped == 0
    assert (target_dir / "2026-04-10" / "log.txt").exists()
    assert (target_dir / "2026-04-11" / "log.txt").exists()
    assert (target_dir / "2026-04-12" / "log.txt").exists()


def test_generate_folders_skips_existing(tmp_path):
    from generate_folders import generate_folders
    target_dir = tmp_path / "push"
    target_dir.mkdir()
    existing = target_dir / "2026-04-10"
    existing.mkdir()
    (existing / "log.txt").write_text("already here")

    today = date(2026, 4, 10)
    created, skipped = generate_folders(target_dir, today, count=2)

    assert created == 1
    assert skipped == 1
    # Existing log.txt is not overwritten
    assert (existing / "log.txt").read_text() == "already here"


def test_generate_folders_log_txt_is_empty(tmp_path):
    from generate_folders import generate_folders
    target_dir = tmp_path / "sleep"
    target_dir.mkdir()

    today = date(2026, 4, 10)
    generate_folders(target_dir, today, count=1)

    log_file = target_dir / "2026-04-10" / "log.txt"
    assert log_file.read_text() == ""
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_generate_folders.py::test_generate_folders_creates_dirs -v
```

Expected: `FAILED` — `ImportError: cannot import name 'generate_folders'`

- [ ] **Step 3: Implement generate_folders function**

Add to `generate_folders.py`:

```python
def generate_folders(target_dir: Path, start: date, count: int) -> tuple[int, int]:
    """Create date folders with empty log.txt. Returns (created, skipped)."""
    created = 0
    skipped = 0
    for i in range(count):
        folder_name = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        folder = target_dir / folder_name
        if folder.exists():
            skipped += 1
        else:
            folder.mkdir(parents=True)
            (folder / "log.txt").write_text("")
            created += 1
    return created, skipped
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_generate_folders.py -v
```

Expected: All tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add generate_folders.py tests/test_generate_folders.py
git commit -m "feat: implement date folder generation with skip logic"
```

---

### Task 5: Wire up main() and end-to-end test

**Files:**
- Modify: `generate_folders.py`
- Modify: `tests/test_generate_folders.py`

- [ ] **Step 1: Write failing end-to-end test**

Add to `tests/test_generate_folders.py`:

```python
def test_main_end_to_end(tmp_path, monkeypatch, capsys):
    from generate_folders import main

    # Set up a fake project root with a push folder
    push_dir = tmp_path / "push"
    push_dir.mkdir()
    monkeypatch.setattr("generate_folders.ROOT", tmp_path)

    with patch("sys.argv", ["generate_folders.py", "push", "--count", "3"]):
        main()

    captured = capsys.readouterr()
    assert "Created: 3" in captured.out
    assert "Skipped: 0" in captured.out
    # Verify at least one date folder with log.txt was created
    date_folders = list(push_dir.iterdir())
    assert len(date_folders) == 3
    assert all((f / "log.txt").exists() for f in date_folders)


def test_main_invalid_target_exits(tmp_path, monkeypatch):
    from generate_folders import main
    monkeypatch.setattr("generate_folders.ROOT", tmp_path)

    with patch("sys.argv", ["generate_folders.py", "invalid_type"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_generate_folders.py::test_main_end_to_end -v
```

Expected: `FAILED` — `ImportError: cannot import name 'main'`

- [ ] **Step 3: Implement main()**

Add to `generate_folders.py`:

```python
def main() -> None:
    args = parse_args()
    validate_target(args.target)
    validate_count(args.count)

    folder_name = FOLDER_MAP[args.target]
    target_dir = ROOT / folder_name

    if not target_dir.exists():
        print(f"Error: target directory '{target_dir}' does not exist.")
        raise SystemExit(1)

    today = date.today()
    created, skipped = generate_folders(target_dir, today, args.count)

    print(f"Target: {folder_name}/")
    print(f"Created: {created} folder(s)")
    print(f"Skipped: {skipped} folder(s) (already existed)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: All 26+ tests `PASSED`

- [ ] **Step 5: Smoke test manually**

```bash
python generate_folders.py push --count 3
```

Expected output:
```
Target: push/
Created: 3 folder(s)
Skipped: 0 folder(s) (already existed)
```

- [ ] **Step 6: Final commit**

```bash
git add generate_folders.py tests/test_generate_folders.py
git commit -m "feat: wire up main() for generate_folders CLI, all tests passing"
```
