from __future__ import annotations

import re

from fshorts.facts.model import fold
from fshorts.facts.sheet import MomentFacts

MAX_WORDS = 7
MAX_PUNCH_WORDS = 3
MAX_TITLE_CHARS = 70
MAX_TITLE_WORDS = 14

# Claims a caption may only make when the facts back them: word pattern -> check on the facts
CLAIMS = [
    (r"\bagain\b|\bsecond\b|\bbrace\b|\bdouble\b", lambda f: f.kind != "goal" or (f.nth_goal or 0) >= 2),
    (r"\bhat[- ]?trick\b|\bthird\b|\btreble\b", lambda f: f.kind == "goal" and f.nth_goal == 3),
    (r"\b(late|last|final|stoppage|dying)\b", lambda f: f.late or (f.minute or 0) >= 85),
    (r"\b(equali[sz]\w*|level|leveller)\b", lambda f: f.kind == "goal" and f.equaliser),
    (r"\b(winner|lead|ahead|in front)\b", lambda f: f.kind == "goal" and f.go_ahead),
    # A goal always changes the score
    (r"\bstill\b", lambda f: f.kind != "goal"),
    (r"\b(penalty|penalties|spot[- ]kick|from the spot|pen)\b", lambda f: f.penalty),
    (r"\bfree[- ]kick\b", lambda f: f.free_kick),
    (r"\bown goal\b", lambda f: f.own_goal),
    (r"\b(goals?|scores?|scored|finish(es|ed)?|nets?|netted|strikes? (again|home))\b", lambda f: f.kind == "goal"),
    (r"\b(saves?|saved|denied|stops?|keeper|no way|says no)\b", lambda f: f.kind in ("shot_saved", "goal")),
    (r"\b(post|bar|crossbar|woodwork)\b", lambda f: f.kind == "woodwork"),
    (r"\b(block|blocked)\b", lambda f: f.kind == "shot_blocked"),
    (r"\b(miss|misses|missed|wide|over the bar)\b", lambda f: f.kind in ("near_miss", "shot_off_target", "woodwork")),
    # Things we can never see from the commentary and the score bug
    (r"\b(header|headed|volley|bicycle|overhead|solo|halfway|chip|chipped|nutmeg|debut|record|history)\b",
     lambda f: False),
    # Restarts and match context the facts never hold; "in 24 minutes" reads as a time span
    (r"\b(throw|throw-in|throws|corner|foul|card|offside|half[- ]time|minutes?)\b", lambda f: False),
]
# Capitalised words that are not names
COMMON = {
    "what", "wait", "watch", "how", "who", "why", "when", "this", "that", "the", "a", "an", "no", "not", "yes",
    "oh", "wow", "omg", "pure", "iconic", "unreal", "insane", "class", "magic", "world", "cup", "fifa", "var",
    "i", "you", "he", "his", "they", "we", "just", "look", "keep", "try", "impossible", "here", "there", "it",
    "goal", "save", "so", "close", "too", "don't", "can't", "never", "ever", "best", "top", "one", "two",
    "and", "or", "but", "of", "for", "from", "to", "in", "on", "at", "with", "by", "is", "was", "be",
}
# All-caps words that are not shouting
CAPS_OK = {"VS", "VAR", "OK", "I"}
TEAM_CLAIM = re.compile(r"\b(lead|leads|ahead|in front|equali[sz]\w*|level)\b")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]")
NUMBER = re.compile(r"\d+")


def problems(line: str, facts: MomentFacts, squad: set[str] = frozenset(), max_words: int = MAX_WORDS) -> list[str]:
    """Why a caption line may not go on screen; empty when it is fine.

    `squad` holds every name part of both line-ups: a squad name that is not this moment's player
    is a wrong name, which is worse than no name.
    """
    found = []
    words = EMOJI.sub(" ", line).split()
    if not words:
        return ["empty"]
    if len(words) > max_words:
        found.append(f"{len(words)} words")
    if len([c for c in EMOJI.findall(line) if c not in "️‍"]) > 2:
        found.append("too many emoji")
    shouted = [w for w in words if w.isupper() and len(w.strip(".,!?…'’")) >= 2 and w.strip(".,!?…") not in CAPS_OK]
    if len(shouted) > 1:
        found.append("shouting")
    if re.search(r"\ba [aeio]\w", line, re.IGNORECASE):
        found.append("bad grammar 'a' before a vowel")
    lowered = line.lower()
    team_claim = TEAM_CLAIM.search(lowered)
    if team_claim and facts.player_team:
        for team in (facts.home, facts.away):
            if team and team != facts.player_team and re.search(rf"\b{re.escape(team.lower())}\b", lowered):
                found.append(f"'{team_claim.group(0)}' given to {team}")
    for pattern, allowed in CLAIMS:
        hit = re.search(pattern, lowered)
        if hit and not allowed(facts):
            found.append(f"unsupported '{hit.group(0)}'")
    allowed_numbers = {str(facts.minute)} if facts.minute else set()
    if facts.score_after:
        allowed_numbers |= set(NUMBER.findall(facts.score_after))
    for number in NUMBER.findall(line):
        if number not in allowed_numbers:
            found.append(f"unsupported number {number}")
    names = {part for name in facts.names() for part in fold(name).split()}
    for word, first in _capitalised(line):
        if word.isupper() and len(word) > 2:
            if fold(word) in squad:
                found.append(f"name in capitals '{word}'")
            continue   # otherwise an emphasis word, "NOWHERE"
        key = fold(word)
        if key in names or key in COMMON:
            continue
        if key in squad:
            found.append(f"wrong player '{word}'")
        elif not first:
            found.append(f"unknown name '{word}'")
    return found


def _capitalised(line: str) -> list[tuple[str, bool]]:
    """Capitalised words with whether each opens a sentence (then it may be a plain adjective)."""
    found, first = [], True
    for token in EMOJI.sub(" ", line).split():
        word = re.sub(r"['’]s$", "", token.strip(" ,;:!?…\"'()")).strip(".")
        if word and word[0].isupper():
            for part in word.split("-") if "-" in word and not word.isupper() else [word]:
                found.append((part, first))
        first = token.endswith((".", "!", "?", "…"))
    return found
