import os
import anthropic


def call_claude(system_prompt: str, user_message: str, model: str = "claude-sonnet-4-6") -> str:
    """Call the Claude API and return the response text."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Run: export ANTHROPIC_API_KEY=your_key_here"
        )
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text
