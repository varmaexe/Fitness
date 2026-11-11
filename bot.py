#!/usr/bin/env python3
# bot.py — Telegram front-end for the Fitness trainer
"""
Send the bot:
  • FitNotes workout text  → filed into <split>/<date>/log.txt, analyzed, feedback sent back
  • A number like 79.9     → weight/<date>.txt  (anything after the number becomes a note)
  • Sleep / nutrition screenshot(s) → read by Claude, shown for confirmation, then saved

Commands: /today  /summary  /show [type] [date]  /analyze <split> [date]  /help

Setup (.env in this folder):
  TELEGRAM_BOT_TOKEN=<token from @BotFather>
  TELEGRAM_ALLOWED_USER_ID=<your numeric id — the bot tells you it on first message>

Run:  .venv/bin/python bot.py
"""
import asyncio
import html
import logging
import os
import re
import secrets
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, filters)

import analyze
from ingest import SPLITS, IngestError, build_exercise_map, guess_split, parse_date, save
from trainer.display import find_feedback
from trainer.extract import ExtractError, extract_screenshots, format_nutrition, format_sleep
from trainer.parsers import parse_calories, parse_sleep, parse_weight
from trainer.render import extract_tldr, to_html, to_telegram_html

ROOT = Path(__file__).resolve().parent
WEIGHT_RE = re.compile(r"^\s*(\d{2,3}(?:[.,]\d{1,2})?)\s*(?:kgs?)?\b\s*(.*)$", re.IGNORECASE | re.DOTALL)
ALBUM_WAIT_S = 2.5
FOLDER = {"sleep": "sleep", "nutrition": "calories"}
EMOJI = {"sleep": "😴", "nutrition": "🍽"}
EXAMPLE = {
    "sleep": "Sleep Time: 6h 8m\nPhysical Recovery: 68%\nMental Recovery: 77%\nDeep: 43m (11%)\nNotes: ...",
    "nutrition": "Calories: 2000\nProtein: 150g\nCarbs: 188g\nFats: 63g\nFiber: 17g\nNotes: ...",
}
HELP = (
    "<b>Send me:</b>\n"
    "• FitNotes workout text (Share → Telegram) → saved, analyzed, feedback back\n"
    "• <code>79.9</code> → today's weight (add a note after it: <code>79.9 morning</code>)\n"
    "• Sleep or nutrition screenshot(s) → I read them, you confirm\n\n"
    "<b>Commands</b>\n"
    "/today — what's logged today\n"
    "/summary — weekly review\n"
    "/show [type] [date] — saved feedback (default: latest)\n"
    "/analyze &lt;split&gt; [date] — re-run analysis"
)

log = logging.getLogger("fitbot")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def msg_date(msg: Message) -> str:
    return msg.date.astimezone().date().isoformat()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


async def allowed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    uid = update.effective_user.id if update.effective_user else None
    owner = context.bot_data.get("owner")
    if owner is None:
        if update.effective_message:
            await update.effective_message.reply_text(
                f"Your Telegram user ID is {uid}.\n"
                f"Add  TELEGRAM_ALLOWED_USER_ID={uid}  to .env and restart the bot.")
        return False
    return uid == owner


def new_pending(context: ContextTypes.DEFAULT_TYPE, entry: dict) -> str:
    token = secrets.token_hex(4)
    context.user_data.setdefault("pending", {})[token] = entry
    return token


async def with_typing(msg: Message, coro):
    """Await a long task while showing 'typing…' in the chat."""
    task = asyncio.ensure_future(coro)
    while not task.done():
        try:
            await msg.chat.send_action(ChatAction.TYPING)
        except Exception:
            pass
        await asyncio.wait({task}, timeout=4.5)
    return task.result()


async def send_feedback(msg: Message, feedback: str, title: str, filename: str) -> None:
    """Short TL;DR as a message + the full feedback as a self-contained HTML file."""
    tldr = to_telegram_html(extract_tldr(feedback))[:3500]
    text = f"<b>{html.escape(title)}</b>\n\n{tldr}"
    try:
        await msg.reply_text(text, parse_mode=ParseMode.HTML)
    except BadRequest:  # odd markup from the model — send it plain
        await msg.reply_text(f"{title}\n\n{extract_tldr(feedback)}"[:4000])
    await msg.reply_document(document=to_html(feedback, title).encode(), filename=filename,
                             caption="Full feedback")


async def run_feedback(msg: Message, split: str, day: str) -> None:
    try:
        _, feedback = await with_typing(msg, asyncio.to_thread(analyze.generate_feedback, split, day))
    except Exception as e:
        log.exception("analysis failed")
        await msg.reply_text(f"✗ Analysis failed: {e}\nThe log is saved — retry with /analyze {split} {day}")
        return
    await send_feedback(msg, feedback, f"{split.upper()} — {day}", f"feedback-{split}-{day}.html")


# ---------------------------------------------------------------------------
# workouts
# ---------------------------------------------------------------------------

async def handle_workout(msg: Message, context, text: str) -> None:
    try:
        day = parse_date(text)
    except IngestError as e:
        await msg.reply_text(f"✗ {e}")
        return
    split, _ = guess_split(text, build_exercise_map(ROOT))
    token = new_pending(context, {"type": "workout", "text": text, "date": day, "split": split})
    if split is None:
        buttons = [[InlineKeyboardButton(s.title(), callback_data=f"split:{token}:{s}") for s in SPLITS]]
        await msg.reply_text(f"New exercises — which split was {day}?",
                             reply_markup=InlineKeyboardMarkup(buttons))
        return
    await save_workout(msg, context, token)


async def save_workout(msg: Message, context, token: str, force: bool = False) -> None:
    entry = context.user_data["pending"][token]
    split, day = entry["split"], entry["date"]
    try:
        dest = save(ROOT, entry["text"], split, day, force=force)
    except IngestError:
        buttons = [[InlineKeyboardButton("Overwrite", callback_data=f"over:{token}"),
                    InlineKeyboardButton("Cancel", callback_data=f"cancel:{token}")]]
        await msg.reply_text(f"⚠️ {split}/{day} already has a different log.",
                             reply_markup=InlineKeyboardMarkup(buttons))
        return
    context.user_data["pending"].pop(token, None)
    await msg.reply_text(f"✓ Saved → {rel(dest)}\n⏳ Analyzing… (about a minute)")
    await run_feedback(msg, split, day)


# ---------------------------------------------------------------------------
# weight
# ---------------------------------------------------------------------------

async def handle_weight(msg: Message, kg: float, note: str) -> None:
    day = msg_date(msg)
    path = ROOT / "weight" / f"{day}.txt"
    old = path.read_text().strip() if path.exists() else ""
    path.parent.mkdir(exist_ok=True)
    path.write_text(f"{kg:g}kg\n" + (f"Notes: {note}\n" if note else ""))
    replaced = f"  (replaced: {old.splitlines()[0]})" if old else ""
    await msg.reply_text(f"⚖️ {kg:g} kg saved for {day}{replaced}")


# ---------------------------------------------------------------------------
# screenshots (sleep / nutrition)
# ---------------------------------------------------------------------------

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await allowed(update, context):
        return
    msg = update.effective_message
    item = msg.photo[-1] if msg.photo else msg.document
    group = msg.media_group_id
    if group:  # album: collect all images of the group, then process once
        albums = context.chat_data.setdefault("albums", {})
        if group in albums:
            albums[group].append(item)
            return
        albums[group] = [item]
        await asyncio.sleep(ALBUM_WAIT_S)
        items = albums.pop(group)
    else:
        items = [item]
    await process_screenshots(msg, context, items)


async def process_screenshots(msg: Message, context, items: list) -> None:
    status = await msg.reply_text("🔍 Reading screenshot…" if len(items) == 1
                                  else f"🔍 Reading {len(items)} screenshots…")
    with tempfile.TemporaryDirectory(prefix="fitbot-") as tmp:
        paths = []
        for i, item in enumerate(items):
            tg_file = await item.get_file()
            suffix = Path(tg_file.file_path or "").suffix or ".jpg"
            path = Path(tmp) / f"shot{i}{suffix}"
            await tg_file.download_to_drive(path)
            paths.append(path)
        try:
            data = await with_typing(msg, asyncio.to_thread(extract_screenshots, paths))
        except ExtractError as e:
            await status.edit_text(f"✗ {e}")
            return

    kind = data["kind"]
    if kind == "unknown":
        await status.edit_text(f"🤔 That doesn't look like sleep or nutrition: {data.get('reason', '')}")
        return
    text = format_sleep(data) if kind == "sleep" else format_nutrition(data)
    if not text:
        await status.edit_text("✗ Couldn't find any numbers in that screenshot.")
        return
    day = _valid_date(data.get("date")) or msg_date(msg)
    token = new_pending(context, {"type": kind, "text": text, "date": day})
    await show_preview(status, context, token, edit=True)


def _valid_date(s) -> str | None:
    try:
        d = date.fromisoformat(str(s))
    except ValueError:
        return None
    return d.isoformat() if d <= date.today() + timedelta(days=1) else None


async def show_preview(msg: Message, context, token: str, edit: bool) -> None:
    entry = context.user_data["pending"][token]
    kind, day = entry["type"], entry["date"]
    path = ROOT / FOLDER[kind] / f"{day}.txt"
    warn = "\n⚠️ Replaces the existing entry for this date." if path.exists() and path.read_text().strip() else ""
    text = (f"{EMOJI[kind]} <b>{kind.title()} — {day}</b>\n"
            f"<pre>{html.escape(entry['text'])}</pre>{warn}")
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Save", callback_data=f"save:{token}"),
         InlineKeyboardButton("📅 −1 day", callback_data=f"prev:{token}")],
        [InlineKeyboardButton("✏️ Fix", callback_data=f"fix:{token}"),
         InlineKeyboardButton("✖ Cancel", callback_data=f"cancel:{token}")],
    ])
    if edit:
        await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=buttons)
    else:
        await msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=buttons)


def valid_entry(kind: str, text: str) -> bool:
    if kind == "sleep":
        return parse_sleep(text)["sleep_time_minutes"] > 0
    return parse_calories(text)["calories"] > 0


# ---------------------------------------------------------------------------
# message + button routing
# ---------------------------------------------------------------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await allowed(update, context):
        return
    msg = update.effective_message
    text = msg.text or ""

    if "FitNotes Workout" in text:
        await handle_workout(msg, context, text)
        return

    fixing = context.user_data.get("fixing")
    if fixing and fixing in context.user_data.get("pending", {}):
        entry = context.user_data["pending"][fixing]
        if not valid_entry(entry["type"], text):
            await msg.reply_text("That doesn't parse — use the same format, e.g.\n"
                                 f"<pre>{html.escape(EXAMPLE[entry['type']])}</pre>",
                                 parse_mode=ParseMode.HTML)
            return
        entry["text"] = text.strip()
        context.user_data.pop("fixing")
        await show_preview(msg, context, fixing, edit=False)
        return

    m = WEIGHT_RE.match(text)
    if m:
        kg = float(m.group(1).replace(",", "."))
        if 30 <= kg <= 250:
            await handle_weight(msg, kg, m.group(2).strip())
            return

    await msg.reply_text(HELP, parse_mode=ParseMode.HTML)


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await allowed(update, context):
        return
    query = update.callback_query
    action, token, *rest = query.data.split(":")
    entry = context.user_data.get("pending", {}).get(token)
    if entry is None:
        await query.answer("This entry expired — send it again.", show_alert=True)
        return
    await query.answer()
    msg = query.message

    if action == "cancel":
        context.user_data["pending"].pop(token, None)
        await msg.edit_text("✖ Cancelled.")
    elif action == "split":
        entry["split"] = rest[0]
        await msg.edit_text(f"Split: {rest[0]}")
        await save_workout(msg, context, token)
    elif action == "over":
        await msg.edit_text("Overwriting…")
        await save_workout(msg, context, token, force=True)
    elif action == "prev":
        entry["date"] = (date.fromisoformat(entry["date"]) - timedelta(days=1)).isoformat()
        await show_preview(msg, context, token, edit=True)
    elif action == "fix":
        context.user_data["fixing"] = token
        await msg.reply_text("Send the corrected entry as text (edit the lines below, add a Notes: line if you like):\n"
                             f"<pre>{html.escape(entry['text'])}</pre>", parse_mode=ParseMode.HTML)
    elif action == "save":
        path = ROOT / FOLDER[entry["type"]] / f"{entry['date']}.txt"
        path.parent.mkdir(exist_ok=True)
        path.write_text(entry["text"].strip() + "\n")
        context.user_data["pending"].pop(token, None)
        await msg.edit_text(f"✓ Saved → {rel(path)}\n<pre>{html.escape(entry['text'])}</pre>",
                            parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await allowed(update, context):
        await update.effective_message.reply_text(HELP, parse_mode=ParseMode.HTML)


def today_status(day: str) -> str:
    def filled(p: Path) -> bool:
        return p.exists() and bool(p.read_text().strip())
    workouts = [s for s in SPLITS + ["cardio"] if filled(ROOT / s / day / "log.txt")]
    rows = [
        ("💪 Workout", ", ".join(workouts) if workouts else None),
        ("😴 Sleep", "logged" if filled(ROOT / "sleep" / f"{day}.txt") else None),
        ("🍽 Nutrition", "logged" if filled(ROOT / "calories" / f"{day}.txt") else None),
        ("⚖️ Weight", f"{parse_weight((ROOT / 'weight' / f'{day}.txt').read_text())['weight_kg']:g} kg"
         if filled(ROOT / "weight" / f"{day}.txt") else None),
    ]
    lines = [f"<b>Today — {day}</b>"]
    lines += [f"{'✅' if v else '❌'} {label}" + (f": {html.escape(v)}" if v else "") for label, v in rows]
    return "\n".join(lines)


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await allowed(update, context):
        msg = update.effective_message
        await msg.reply_text(today_status(msg_date(msg)), parse_mode=ParseMode.HTML)


async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await allowed(update, context):
        return
    msg = update.effective_message
    day = msg_date(msg)
    await msg.reply_text("⏳ Building weekly summary… (about a minute)")
    try:
        _, feedback = await with_typing(msg, asyncio.to_thread(analyze.generate_summary, day))
    except Exception as e:
        log.exception("summary failed")
        await msg.reply_text(f"✗ Summary failed: {e}")
        return
    await send_feedback(msg, feedback, f"WEEKLY SUMMARY — {day}", f"summary-{day}.html")


def _split_args(args: list[str]) -> tuple[str | None, str | None]:
    stype = next((a for a in args if a in analyze.WORKOUT_TYPES), None)
    day = next((a for a in args if a not in analyze.WORKOUT_TYPES), None)
    return stype, day


async def cmd_show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await allowed(update, context):
        return
    msg = update.effective_message
    stype, day = _split_args(context.args)
    path = find_feedback(ROOT, analyze.WORKOUT_TYPES, stype, day)
    if path is None:
        await msg.reply_text("No feedback found.")
        return
    parts = path.relative_to(ROOT).parts
    if len(parts) == 3:
        title, name = f"{parts[0].upper()} — {parts[1]}", f"feedback-{parts[0]}-{parts[1]}.html"
    else:
        title, name = path.stem.replace("summary-", "WEEKLY SUMMARY — "), f"{path.stem}.html"
    await send_feedback(msg, path.read_text(), title, name)


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await allowed(update, context):
        return
    msg = update.effective_message
    stype, day = _split_args(context.args)
    if stype is None:
        await msg.reply_text("Usage: /analyze <push|pull|legs|arms|cardio> [YYYY-MM-DD]")
        return
    day = day or msg_date(msg)
    await msg.reply_text(f"⏳ Analyzing {stype} {day}…")
    await run_feedback(msg, stype, day)


# ---------------------------------------------------------------------------

def main() -> None:
    load_env(ROOT / ".env")
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # its INFO lines contain the bot token

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        sys.exit("TELEGRAM_BOT_TOKEN is missing. Put  TELEGRAM_BOT_TOKEN=<token>  in .env")
    owner = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "").strip()

    app = Application.builder().token(token).concurrent_updates(True).build()
    app.bot_data["owner"] = int(owner) if owner else None
    if not owner:
        log.warning("TELEGRAM_ALLOWED_USER_ID not set — the bot will only reply with your user ID.")

    app.add_handler(CommandHandler(["start", "help"], cmd_help))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("show", cmd_show))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_button))

    log.info("Bot running. Ctrl-C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
