import re

def strip_ansi(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    # Catch standard escapes (\x1b, \033), terminal artifacts (║), and raw string representations
    return re.sub(r'(\x1b|\033|║|\\x1b|\\033)\[[0-9;]*m', '', text)
