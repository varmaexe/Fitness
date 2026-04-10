# Design: generate_folders.py

**Date:** 2026-04-10  
**Status:** Approved

## Summary

A CLI utility script that generates consecutive date-named folders (YYYY-MM-DD format) inside a given target workout directory, starting from today and going forward. Each folder gets an empty `log.txt` file ready for workout data entry.

## Usage

```bash
python generate_folders.py <target> [--count N]
```

**Arguments:**
- `target` — required positional arg, name of workout folder (e.g., `push`, `pull`, `cardio`, `sleep`, `weight`, `legs-abs`, `arms`)
- `--count` — optional, number of folders to create, default `10`, max `10`

**Example:**
```bash
python generate_folders.py push          # creates 10 date folders in push/
python generate_folders.py cardio --count 5  # creates 5 date folders in cardio/
```

## Folder Structure Generated

```
push/
  2026-04-10/
    log.txt   (empty)
  2026-04-11/
    log.txt   (empty)
  ...
  2026-04-19/
    log.txt   (empty)
```

## Behavior

- Dates start from today and go forward consecutively
- Skip silently if a date folder already exists (no overwrite)
- Validate that target folder exists in the project root before creating
- Print a summary of folders created vs skipped

## Error Handling

- Invalid target name → print available targets and exit with error
- Count out of range (< 1 or > 10) → print usage and exit with error

## Files

- **Location:** `/home/saiverma/Development/Fitness/generate_folders.py`
- **Dependencies:** stdlib only (`argparse`, `datetime`, `pathlib`, `os`)
