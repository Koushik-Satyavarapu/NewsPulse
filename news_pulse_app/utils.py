import re
from typing import List

def estimate_read_time(text: str) -> int:
    # Rough estimate: 200 words per minute
    words = re.findall(r"\w+", text or "")
    return max(1, int(len(words) / 200) + (1 if len(words) % 200 else 0))

CATEGORIES = ["world", "nation", "business", "technology", "entertainment", "sports", "science", "health"]
