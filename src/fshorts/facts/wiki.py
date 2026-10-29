from __future__ import annotations

import re
import urllib.parse
import urllib.request
from pathlib import Path

from fshorts.facts.model import GoalFact, MatchFacts, Player, Team

USER_AGENT = "fshorts/0.1 (football shorts research tool)"
# {{#invoke:Football box|main ...}} on newer pages, {{Football box ...}} on older ones
BOX_START = re.compile(r"\{\{(?:#invoke:)?Football box")
LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
# {{fb-rt|FRA|1974}} or {{#invoke:flagg|main|unpre|avar=fb|BRA}}
TEAM = re.compile(r"\|team([12])=\{\{[^}]*?\|([A-Z]{3})(?:\|[^}]*)?\}\}")
LINEUP_ROW = re.compile(r"^\|\s*([A-Z]{2,3})\s*\|\|\s*'''(\d+)'''\s*\|\|\s*(.+)$")
GOAL_ROW = re.compile(r"^\*\s*(\[\[[^\]]+\]\])\s*\{\{goal\|([^}]*)\}\}")
MINUTE = re.compile(r"^\d+(\+\d+)?$")


class WikipediaPages:
    """Raw wikitext of a page, cached on disk so a match is fetched once."""

    def __init__(self, cache: Path) -> None:
        self._cache = cache

    def raw(self, title: str) -> str:
        path = self._cache / (re.sub(r"[^\w-]+", "_", title) + ".txt")
        if path.is_file():
            return path.read_text(encoding="utf-8")
        url = "https://en.wikipedia.org/w/index.php?" + urllib.parse.urlencode({"title": title, "action": "raw"})
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=30) as r:
            text = r.read().decode("utf-8")
        self._cache.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return text


def parse_match(wikitext: str, home: str, away: str, home_name: str = "", away_name: str = "") -> MatchFacts:
    """Line-ups and goals of one match from its Football box and the line-up tables after it."""
    section = _match_section(wikitext, home, away)
    goals = _goals(section, home, away)
    lineups = _lineups(section)
    if len(lineups) < 2:
        raise ValueError(f"no line-up tables for {home} vs {away}")
    return MatchFacts(Team(home, home_name or home, lineups[0]), Team(away, away_name or away, lineups[1]), goals)


def _match_section(wikitext: str, home: str, away: str) -> str:
    boxes = BOX_START.split(wikitext)[1:]
    for box in boxes:
        teams = dict(TEAM.findall(box[:2000]))
        if teams.get("1") == home and teams.get("2") == away:
            return box
    raise ValueError(f"no Football box for {home} vs {away}")


def _goals(section: str, home: str, away: str) -> list[GoalFact]:
    goals: list[GoalFact] = []
    side = None
    for line in section.splitlines():
        line = line.strip()
        if line.startswith("|goals1"):
            side = home
        elif line.startswith("|goals2"):
            side = away
        elif line.startswith("|") and side:
            side = None
        if side is None:
            continue
        match = GOAL_ROW.match(line)
        if not match:
            continue
        target, shown = _link(match.group(1))
        parts = match.group(2).split("|")
        for index, part in enumerate(parts):
            if MINUTE.match(part.strip()):
                note = parts[index + 1].strip() if index + 1 < len(parts) and not MINUTE.match(parts[index + 1].strip()) else ""
                base, _, extra = part.strip().partition("+")
                # Wikipedia lists an own goal under the team it counts for
                goals.append(GoalFact(side, shown, target, int(base), int(extra or 0), note))
    return sorted(goals, key=lambda g: (g.minute, g.added))


def _lineups(section: str) -> list[list[Player]]:
    tables: list[list[Player]] = []
    for line in section.splitlines():
        if line.startswith("{|") and "cellpadding" in line:
            tables.append([])
            continue
        match = LINEUP_ROW.match(line.strip())
        if match and tables:
            position, number, rest = match.groups()
            link = LINK.search(rest)
            if link is None:
                continue
            target, shown = _link(link.group(0))
            starter = "{{subon" not in rest
            tables[-1].append(Player(shown, target, int(number), position, starter))
    return [t for t in tables if t]


def _link(text: str) -> tuple[str, str]:
    """[[Target (disambiguation)|Shown]] -> (clean target, shown)."""
    match = LINK.search(text)
    target = re.sub(r"\s*\(.*?\)", "", match.group(1)).strip()
    return target, (match.group(2) or target).strip()
