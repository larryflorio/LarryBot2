"""Telegram safety helpers.

This module wraps Telegram message-sending calls so that:
1. We try to send the text as-is (to preserve intended bold / italics etc.).
2. If Telegram rejects the text with a *Can't parse entities* error, we
   automatically escape the entire payload with the official
   `telegram.helpers.escape_markdown` helper and resend.

By funnelling all outbound messages through these helpers we avoid the
"unescaped character" crashes while minimising double-escaping.  New code
should import and use `safe_edit` / `safe_send` instead of calling the
underlying telegram methods directly.
"""

from typing import Any, Callable, Awaitable, Optional
import telegram.error
from telegram.helpers import escape_markdown
from functools import wraps
import re

DEFAULT_PARSE_MODE = "MarkdownV2"

async def _attempt_send(fn: Callable[..., Awaitable], *, text: str, parse_mode: str = DEFAULT_PARSE_MODE, **kwargs):
    """Try to send a message; on Markdown parse failure auto-escape and retry.

    We intentionally pass the *text* argument positionally so that call
    spies/fixtures that inspect ``call_args[0][0]`` (used throughout the test
    suite) continue to work.  All remaining parameters are passed by keyword
    to preserve clarity.
    """

    def _call(positional_text: str, pm: Optional[str]):
        """Helper to invoke *fn* with the required argument order."""
        return fn(positional_text, parse_mode=pm, **kwargs)

    try:
        return await _call(text, parse_mode)
    except telegram.error.BadRequest as exc:
        if "Can't parse entities" not in str(exc):
            raise  # unrelated error

        # First fallback – try plain-text (strip backslashes, no parse_mode)
        plain_text = re.sub(r"\\([_\*\[\]\(\)~`>#\+\-=|{}\.\!])", r"\1", str(text))
        try:
            return await _call(plain_text, None)
        except telegram.error.BadRequest:
            # Second fallback – fully escaped MarkdownV2
            safe_text = escape_markdown(str(text), version=2)
            return await _call(safe_text, parse_mode)


aSyncEditFunc = Callable[..., Awaitable[Any]]

def safe_edit(edit_func: aSyncEditFunc, *args, text: Optional[str] = None, reply_markup=None, **kwargs):
    """Safe wrapper for ``edit_message_text``.

    Usage patterns supported:

        await safe_edit(query.edit_message_text, "hello")
        await safe_edit(query.edit_message_text, text="hello")

    Additional kwargs are forwarded to Telegram.  ``reply_markup`` is accepted
    as a top-level keyword (matching the Telegram API) but we leave it in
    **kwargs so that the call signature remains flexible.
    """

    # Backwards-compatibility: allow text as first positional argument.
    if text is None and args:
        text = args[0]
        args = args[1:]

    if args:
        raise TypeError("safe_edit(): unexpected positional arguments after text")

    return _attempt_send(edit_func, text=text, reply_markup=reply_markup, **kwargs)


def safe_send(send_func: aSyncEditFunc, *args, text: Optional[str] = None, reply_markup=None, **kwargs):
    """Safe wrapper for ``reply_text`` / ``send_message``. Supports positional text."""

    if text is None and args:
        text = args[0]
        args = args[1:]

    if args:
        raise TypeError("safe_send(): unexpected positional arguments after text")

    return _attempt_send(send_func, text=text, reply_markup=reply_markup, **kwargs)