import re
from typing import Optional

REGEX_TICKER = re.compile(r"\$[A-Z]{2,10}")
REGEX_ETH    = re.compile(r"0x[a-fA-F0-9]{40}")
REGEX_SOL    = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")


def contains_token_related(text: Optional[str]) -> bool:
    if not text:
        return False
    return bool(REGEX_TICKER.search(text) or REGEX_ETH.search(text) or REGEX_SOL.search(text))
