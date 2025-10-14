from datetime import datetime
from typing import Optional


def bold(text: str) -> str:
    return f"*{escape(text)}*"


def code(text: str) -> str:
    return f"`{escape(text)}`"


def escape(text: str) -> str:
    # Minimal escape for MarkdownV2
    replacements = {
        "_": "\\_",
        "*": "\\*",
        "[": "\\[",
        "]": "\\]",
        "(": "\\(",
        ")": "\\)",
        "~": "\\~",
        "`": "\\`",
        ">": "\\>",
        "#": "\\#",
        "+": "\\+",
        "-": "\\-",
        "=": "\\=",
        "|": "\\|",
        "{": "\\{",
        "}": "\\}",
        ".": "\\.",
        "!": "\\!",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def human_dt(dt: Optional[datetime]) -> str:
    if not dt:
        return "Not Applicable"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def is_valid_token(token: str) -> bool:
    # Basic BotFather token format validation
    import re
    return bool(re.match(r"^\\d+:[A-Za-z0-9_-]{30,}$", token))