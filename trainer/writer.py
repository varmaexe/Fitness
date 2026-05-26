from pathlib import Path
from datetime import datetime


def write_feedback(session_folder: Path, feedback_text: str) -> Path:
    """Write feedback.md into the session's date folder. Returns the file path."""
    session_folder.mkdir(parents=True, exist_ok=True)
    output_file = session_folder / "feedback.md"
    header = f"<!-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} -->\n\n"
    output_file.write_text(header + feedback_text)
    return output_file
