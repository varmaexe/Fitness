# trainer/render.py
"""Turn feedback markdown into a phone-friendly HTML file and a short Telegram summary."""
import html
import re

import markdown

_GENERATED_RE = re.compile(r"^<!--.*?-->\s*", re.DOTALL)
_TLDR_RE = re.compile(
    r"^#{1,6}\s*(?:\d+\.\s*)?\**TL;?DR\**:?\s*$\n(.*?)(?=^#{1,6}\s|^-{3,}\s*$|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)

CSS = """
:root { --bg:#ffffff; --fg:#1d1d1f; --muted:#6e6e73; --line:#e5e5ea; --accent:#0a7cff; --code:#f2f2f7; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#111113; --fg:#ececf1; --muted:#9a9aa2; --line:#2c2c30; --accent:#4da3ff; --code:#1c1c1f; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font: 16px/1.55 -apple-system, "Segoe UI", Roboto, system-ui, sans-serif; }
main { max-width: 720px; margin: 0 auto; padding: 20px 16px 48px; }
header { border-bottom: 1px solid var(--line); margin-bottom: 8px; padding-bottom: 12px; }
header h1 { font-size: 1.35rem; margin: 0; }
header p { color: var(--muted); margin: 4px 0 0; font-size: .9rem; }
h1, h2, h3 { line-height: 1.25; }
h2 { font-size: 1.15rem; margin-top: 1.8em; color: var(--accent); }
h3 { font-size: 1.02rem; margin-top: 1.4em; }
hr { border: 0; border-top: 1px solid var(--line); margin: 1.5em 0; }
code { background: var(--code); padding: .1em .35em; border-radius: 4px; font-size: .9em; }
.table-wrap { overflow-x: auto; margin: 1em 0; }
table { border-collapse: collapse; width: 100%; font-size: .9rem; }
th, td { border: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: var(--code); }
ul, ol { padding-left: 1.3em; }
li { margin: .25em 0; }
"""


def strip_generated(md: str) -> str:
    return _GENERATED_RE.sub("", md, count=1)


def extract_tldr(md: str, fallback_chars: int = 500) -> str:
    """Return the TL;DR section's body (markdown); fall back to the start of the text."""
    md = strip_generated(md)
    m = _TLDR_RE.search(md)
    if m and m.group(1).strip():
        return m.group(1).strip()
    body = re.sub(r"^#{1,6}\s.*$", "", md, flags=re.MULTILINE).strip()
    return body[:fallback_chars].rstrip() + ("…" if len(body) > fallback_chars else "")


def to_telegram_html(md: str) -> str:
    """Very small markdown → Telegram HTML (b, i, code only; everything else plain)."""
    out = html.escape(md, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"^\s*[-*]\s+", "• ", out, flags=re.MULTILINE)
    return out


def to_html(md: str, title: str, subtitle: str = "") -> str:
    """Self-contained HTML page (inline CSS, no external requests)."""
    body = markdown.markdown(strip_generated(md), extensions=["tables", "sane_lists"])
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    sub = f"<p>{html.escape(subtitle)}</p>" if subtitle else ""
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
        f"<body><main><header><h1>{html.escape(title)}</h1>{sub}</header>{body}</main></body></html>"
    )
