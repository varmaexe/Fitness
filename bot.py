#!/usr/bin/env python3
# bot.py — Telegram front-end for the Fitness trainer
"""
Send the bot:
  • FitNotes workout text  → filed into <split>/<date>/log.txt, analyzed, feedback sent back
  • A number like 79.9     → weight/<date>.txt  (anything after the number becomes a note)
  • Sleep / nutrition screenshot(s) → read by Claude, shown for confirmation, then saved
  • Typed sleep / nutrition ("Sleep Time: 7h 10m", "Calories: 2400") → same confirmation

Commands: /today  /summary  /show [type] [date]  /analyze <split> [date]  /undo  /help

Reminders (sent only when something is missing) and the Sunday summary run on a
schedule; every save is git-committed (only the files the bot wrote).

Setup (.env in this folder):
  TELEGRAM_BOT_TOKEN=<token from @BotFather>
  TELEGRAM_ALLOWED_USER_ID=<your numeric id — the bot tells you it on first message>
Optional (defaults shown; "off" disables):
  FITBOT_MORNING=09:00        weigh-in reminder if today's weight isn't logged
  FITBOT_EVENING=21:00        checklist of what's still missing today
  FITBOT_SUMMARY=sun 20:00    weekly summary, sent automatically
  FITBOT_GIT=commit           commit | push | off

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
from datetime import date, datetime, time, timedelta
from pathlib import Path

from telegram import Bot, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest, NetworkError
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, PersistenceInput, PicklePersistence, filters)

import analyze
from ingest import SPLITS, IngestError, build_exercise_map, guess_split, normalize_log, parse_date, save
from trainer.display import find_feedback
from trainer.extract import ExtractError, extract_screenshots, format_nutrition, format_sleep
from trainer.parsers import detect_manual_entry, parse_calories, parse_sleep, parse_weight
from trainer.render import extract_tldr, to_html, to_telegram_html
from trainer.tracking import git_commit, restore, snapshot, weight_trend

ROOT = Path(__file__).resolve().parent
WEIGHT_RE = re.compile(r"^\s*(\d{2,3}(?:[.,]\d{1,2})?)\s*(?:kgs?)?\b\s*(.*)$", re.IGNORECASE | re.DOTALL)
ALBUM_WAIT_S = 2.5
MAX_PENDING = 20
ALBUMS: dict[str, list] = {}  # media_group_id -> images; transient, so not persisted
DAYS = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}  # PTB numbering
COMMANDS = [
    ("today", "What's logged today"),
    ("summary", "Weekly review"),
    ("show", "Saved feedback: /show [type] [date]"),
    ("analyze", "Re-run analysis: /analyze <split> [date]"),
    ("undo", "Undo the last save"),
    ("help", "What I can do"),
]
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
    "• Sleep or nutrition screenshot(s) → I read them, you confirm\n"
    "• Or type it: <code>Sleep Time: 7h 10m</code> / <code>Calories: 2400</code> "
    "(more lines optional, e.g. <code>Protein: 170g</code>, <code>Notes: ...</code>)\n\n"
    "<b>Commands</b>\n"
    "/today — what's logged today\n"
    "/summary — weekly review\n"
    "/show [type] [date] — saved feedback (default: latest)\n"
    "/analyze &lt;split&gt; [date] — re-run analysis\n"
    "/undo — undo the last save"
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
    pending = context.user_data.setdefault("pending", {})
    pending[token] = entry
    while len(pending) > MAX_PENDING:  # drop abandoned previews so the state file stays small
        pending.pop(next(iter(pending)))
    return token


def filled(p: Path) -> bool:
    return p.exists() and bool(p.read_text().strip())


async def commit(context: ContextTypes.DEFAULT_TYPE, paths: list[Path], message: str) -> None:
    mode = context.bot_data.get("git", "commit")
    if mode != "off":
        await asyncio.to_thread(git_commit, ROOT, paths, message, mode == "push")


def remember_undo(context: ContextTypes.DEFAULT_TYPE, label: str, snap: dict) -> None:
    context.user_data["undo"] = {"label": label, "files": snap}


async def with_typing(bot: Bot, chat_id: int, coro):
    """Await a long task while showing 'typing…' in the chat."""
    task = asyncio.ensure_future(coro)
    while not task.done():
        try:
            await bot.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass
        await asyncio.wait({task}, timeout=4.5)
    return task.result()


async def send_feedback(bot: Bot, chat_id: int, feedback: str, title: str, filename: str) -> None:
    """Short TL;DR as a message + the full feedback as a self-contained HTML file."""
    tldr = to_telegram_html(extract_tldr(feedback))[:3500]
    text = f"<b>{html.escape(title)}</b>\n\n{tldr}"
    try:
        await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
    except BadRequest:  # odd markup from the model — send it plain
        await bot.send_message(chat_id, f"{title}\n\n{extract_tldr(feedback)}"[:4000])
    await bot.send_document(chat_id, document=to_html(feedback, title).encode(), filename=filename,
                            caption="Full feedback")


async def run_feedback(msg: Message, context, split: str, day: str) -> None:
    bot, chat = context.bot, msg.chat_id
    try:
        path, feedback = await with_typing(bot, chat, asyncio.to_thread(analyze.generate_feedback, split, day))
    except Exception as e:
        log.exception("analysis failed")
        await msg.reply_text(f"✗ Analysis failed: {e}\nThe log is saved — retry with /analyze {split} {day}")
        return
    await commit(context, [path], f"feedback({split}): {day}")
    await send_feedback(bot, chat, feedback, f"{split.upper()} — {day}", f"feedback-{split}-{day}.html")


# ---------------------------------------------------------------------------
# workouts
# ---------------------------------------------------------------------------

async def handle_workout(msg: Message, context, text: str) -> None:
    text = normalize_log(text)  # Telegram strips FitNotes' **bold** exercise headers
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
    folder = ROOT / split / day
    snap = snapshot(ROOT, [folder / "log.txt", folder / "feedback.md"])
    try:
        dest = save(ROOT, entry["text"], split, day, force=force)
    except IngestError:
        buttons = [[InlineKeyboardButton("Overwrite", callback_data=f"over:{token}"),
                    InlineKeyboardButton("Cancel", callback_data=f"cancel:{token}")]]
        await msg.reply_text(f"⚠️ {split}/{day} already has a different log.",
                             reply_markup=InlineKeyboardMarkup(buttons))
        return
    context.user_data["pending"].pop(token, None)
    remember_undo(context, f"{split} workout {day}", snap)
    await commit(context, [dest], f"log({split}): {day}")
    await msg.reply_text(f"✓ Saved → {rel(dest)}\n⏳ Analyzing… (about a minute)")
    await run_feedback(msg, context, split, day)


# ---------------------------------------------------------------------------
# weight
# ---------------------------------------------------------------------------

async def handle_weight(msg: Message, context, kg: float, note: str) -> None:
    day = msg_date(msg)
    path = ROOT / "weight" / f"{day}.txt"
    snap = snapshot(ROOT, [path])
    old = path.read_text().strip() if path.exists() else ""
    path.parent.mkdir(exist_ok=True)
    path.write_text(f"{kg:g}kg\n" + (f"Notes: {note}\n" if note else ""))
    remember_undo(context, f"weight {day}", snap)
    await commit(context, [path], f"log(weight): {day}")
    replaced = f"  (replaced: {old.splitlines()[0]})" if old else ""
    trend = weight_trend(ROOT, day)
    await msg.reply_text(f"⚖️ {kg:g} kg saved for {day}{replaced}" + (f"\n📈 {trend}" if trend else ""))


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
        if group in ALBUMS:
            ALBUMS[group].append(item)
            return
        ALBUMS[group] = [item]
        await asyncio.sleep(ALBUM_WAIT_S)
        items = ALBUMS.pop(group)
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
            data = await with_typing(context.bot, msg.chat_id, asyncio.to_thread(extract_screenshots, paths))
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
        if valid_entry(entry["type"], text):
            entry["text"] = text.strip()
            context.user_data.pop("fixing")
            await show_preview(msg, context, fixing, edit=False)
            return
        if not WEIGHT_RE.match(text):  # a bare weight still gets logged below
            await msg.reply_text("That doesn't parse — use the same format, e.g.\n"
                                 f"<pre>{html.escape(EXAMPLE[entry['type']])}</pre>",
                                 parse_mode=ParseMode.HTML)
            return

    typed = detect_manual_entry(text)
    if typed:  # typed sleep/nutrition, e.g. "Sleep Time: 4h 20m" — same preview as a screenshot
        kind, entry_text = typed
        token = new_pending(context, {"type": kind, "text": entry_text, "date": msg_date(msg)})
        await show_preview(msg, context, token, edit=False)
        return

    m = WEIGHT_RE.match(text)
    if m:
        kg = float(m.group(1).replace(",", "."))
        if 30 <= kg <= 250:
            await handle_weight(msg, context, kg, m.group(2).strip())
            return

    await msg.reply_text(HELP, parse_mode=ParseMode.HTML)


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await allowed(update, context):
        return
    query = update.callback_query
    action, token, *rest = query.data.split(":")
    if action == "undo":
        await query.answer()
        await do_undo(query.message, context, token)
        return
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
        snap = snapshot(ROOT, [path])
        path.parent.mkdir(exist_ok=True)
        path.write_text(entry["text"].strip() + "\n")
        context.user_data["pending"].pop(token, None)
        remember_undo(context, f"{entry['type']} {entry['date']}", snap)
        await commit(context, [path], f"log({entry['type']}): {entry['date']}")
        await msg.edit_text(f"✓ Saved → {rel(path)}\n<pre>{html.escape(entry['text'])}</pre>",
                            parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await allowed(update, context):
        await update.effective_message.reply_text(HELP, parse_mode=ParseMode.HTML)


def today_rows(day: str) -> list[tuple[str, str | None]]:
    workouts = [s for s in SPLITS + ["cardio"] if filled(ROOT / s / day / "log.txt")]
    rows = [
        ("💪 Workout", ", ".join(workouts) if workouts else None),
        ("😴 Sleep", "logged" if filled(ROOT / "sleep" / f"{day}.txt") else None),
        ("🍽 Nutrition", "logged" if filled(ROOT / "calories" / f"{day}.txt") else None),
        ("⚖️ Weight", f"{parse_weight((ROOT / 'weight' / f'{day}.txt').read_text())['weight_kg']:g} kg"
         if filled(ROOT / "weight" / f"{day}.txt") else None),
    ]
    return rows


def today_status(day: str, rows: list | None = None) -> str:
    rows = rows if rows is not None else today_rows(day)
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
    await msg.reply_text("⏳ Building weekly summary… (about a minute)")
    await send_summary(context, msg.chat_id, msg_date(msg))


async def send_summary(context, chat_id: int, day: str) -> None:
    try:
        path, feedback = await with_typing(context.bot, chat_id,
                                           asyncio.to_thread(analyze.generate_summary, day))
    except Exception as e:
        log.exception("summary failed")
        await context.bot.send_message(chat_id, f"✗ Summary failed: {e}")
        return
    await commit(context, [path], f"summary: {day}")
    await send_feedback(context.bot, chat_id, feedback, f"WEEKLY SUMMARY — {day}", f"summary-{day}.html")


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
    await send_feedback(context.bot, msg.chat_id, path.read_text(), title, name)


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
    await run_feedback(msg, context, stype, day)


async def cmd_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await allowed(update, context):
        return
    msg = update.effective_message
    undo = context.user_data.get("undo")
    if not undo:
        await msg.reply_text("Nothing to undo.")
        return
    token = secrets.token_hex(4)
    undo["token"] = token
    lines = [f"• {r}: " + ("delete" if c is None else "restore previous version") for r, c in undo["files"].items()]
    buttons = [[InlineKeyboardButton("↩️ Undo", callback_data=f"undo:{token}"),
                InlineKeyboardButton("✖ Keep", callback_data=f"cancel:{token}")]]
    context.user_data.setdefault("pending", {})[token] = {"type": "undo"}
    await msg.reply_text(f"Undo <b>{html.escape(undo['label'])}</b>?\n" + html.escape("\n".join(lines)),
                         parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def do_undo(msg: Message, context, token: str) -> None:
    undo = context.user_data.get("undo")
    context.user_data.get("pending", {}).pop(token, None)
    if not undo or undo.get("token") != token:
        await msg.edit_text("Nothing to undo (already undone, or something newer was saved).")
        return
    touched = restore(ROOT, undo["files"])
    context.user_data.pop("undo")
    await commit(context, touched, f"undo: {undo['label']}")
    await msg.edit_text(f"↩️ Undone: {undo['label']}")


# ---------------------------------------------------------------------------
# scheduled jobs
# ---------------------------------------------------------------------------

async def job_morning(context: ContextTypes.DEFAULT_TYPE) -> None:
    day = date.today().isoformat()
    if not filled(ROOT / "weight" / f"{day}.txt"):
        await context.bot.send_message(context.job.chat_id, "⚖️ Morning weigh-in? Just send the number.")


async def job_evening(context: ContextTypes.DEFAULT_TYPE) -> None:
    day = date.today().isoformat()
    rows = today_rows(day)
    if any(v is None for _, v in rows):
        await context.bot.send_message(context.job.chat_id, today_status(day, rows) + "\n\nStill time to log the ❌ ones.",
                                       parse_mode=ParseMode.HTML)


async def job_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    day = date.today().isoformat()
    if (ROOT / f"summary-{day}.md").exists():
        return  # already ran /summary today
    await send_summary(context, context.job.chat_id, day)


def parse_schedule(value: str, default: str) -> tuple[tuple[int, ...], time] | None:
    """'09:00' → every day at 09:00; 'sun 20:00' → Sundays; 'off' → None."""
    value = (value or default).strip().lower()
    if value in ("off", "none", "0", ""):
        return None
    parts = value.split()
    days = tuple(DAYS[d] for d in parts[0].split(",")) if len(parts) == 2 else tuple(range(7))
    hh, mm = parts[-1].split(":")
    tz = datetime.now().astimezone().tzinfo
    return days, time(int(hh), int(mm), tzinfo=tz)


def schedule_jobs(app: Application, chat_id: int) -> None:
    jobs = [("morning", job_morning, "FITBOT_MORNING", "09:00"),
            ("evening", job_evening, "FITBOT_EVENING", "21:00"),
            ("summary", job_summary, "FITBOT_SUMMARY", "sun 20:00")]
    for name, fn, env, default in jobs:
        try:
            sched = parse_schedule(os.environ.get(env, ""), default)
        except (KeyError, ValueError):
            log.warning("Bad %s=%r — expected HH:MM, 'sun 20:00' or 'off'", env, os.environ.get(env))
            continue
        if sched:
            days, at = sched
            app.job_queue.run_daily(fn, at, days=days, chat_id=chat_id, name=name)
            log.info("Scheduled %s at %s on days %s", name, at.strftime("%H:%M"), days)


# ---------------------------------------------------------------------------
# errors + startup
# ---------------------------------------------------------------------------

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    log.error("Unhandled error", exc_info=err)
    if isinstance(err, NetworkError):  # transient; polling retries on its own
        return
    owner = context.bot_data.get("owner")
    if owner:
        try:
            await context.bot.send_message(owner, f"⚠️ Bot error: {type(err).__name__}: {err}"[:1000])
        except Exception:
            log.exception("couldn't report error to owner")


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands([BotCommand(c, d) for c, d in COMMANDS])


# ---------------------------------------------------------------------------

def main() -> None:
    load_env(ROOT / ".env")
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # its INFO lines contain the bot token

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        sys.exit("TELEGRAM_BOT_TOKEN is missing. Put  TELEGRAM_BOT_TOKEN=<token>  in .env")
    owner = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "").strip()

    # Generous timeouts: the default 5s read timeout aborts on a briefly slow network.
    # Pending previews, Fix mode and /undo survive restarts.
    persistence = PicklePersistence(ROOT / ".bot-state.pickle",
                                    store_data=PersistenceInput(bot_data=False, chat_data=False))
    app = (Application.builder().token(token).concurrent_updates(True).persistence(persistence)
           .connect_timeout(15).read_timeout(30).write_timeout(60).media_write_timeout(120)
           .post_init(post_init).build())
    app.bot_data["owner"] = int(owner) if owner else None
    app.bot_data["git"] = os.environ.get("FITBOT_GIT", "commit").strip().lower()
    if owner:
        schedule_jobs(app, int(owner))  # private chat id == user id
    else:
        log.warning("TELEGRAM_ALLOWED_USER_ID not set — the bot will only reply with your user ID.")

    app.add_handler(CommandHandler(["start", "help"], cmd_help))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("show", cmd_show))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(CommandHandler("undo", cmd_undo))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_error_handler(on_error)

    log.info("Bot running. Ctrl-C to stop.")
    # bootstrap_retries=-1: keep retrying at startup instead of exiting when the
    # network isn't up yet (e.g. right after boot or a Wi-Fi drop).
    app.run_polling(allowed_updates=Update.ALL_TYPES, bootstrap_retries=-1)


if __name__ == "__main__":
    main()
