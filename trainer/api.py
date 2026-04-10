import subprocess


def call_claude(system_prompt: str, user_message: str, model: str = "claude-sonnet-4-6") -> str:
    """Call Claude via the Claude Code CLI and return the response text."""
    result = subprocess.run(
        ["claude", "-p", user_message, "--system-prompt", system_prompt, "--model", model, "--output-format", "text"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {result.stderr.strip()}")
    return result.stdout.strip()
