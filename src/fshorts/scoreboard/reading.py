from __future__ import annotations

import re
from dataclasses import dataclass

TEAM_CODE = re.compile(r"^[A-Z]{3}$")
SCORE_DIGITS = re.compile(r"^\d{1,2}$")
CLOCK = re.compile(r"^(\d{1,3})[:.](\d{2})$")
# Rows of the score bug are a few pixels apart; anything further is another graphic
SAME_ROW_PIXELS = 15


@dataclass(frozen=True)
class OcrToken:
    x: float
    y: float
    text: str
    confidence: float


@dataclass(frozen=True)
class ScoreReading:
    time: float
    home_code: str
    away_code: str
    home: int
    away: int
    clock_seconds: int | None

    @property
    def score(self) -> tuple[int, int]:
        return self.home, self.away

    def to_dict(self) -> dict:
        return {
            "time": self.time, "home_code": self.home_code, "away_code": self.away_code,
            "home": self.home, "away": self.away, "clock_seconds": self.clock_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScoreReading:
        return cls(**data)


class ScoreBugParser:
    """Turns OCR tokens of the score-bug region into "HOME h - a AWAY" plus the match clock.

    Layout-agnostic: it looks for two three-letter team codes on one row and the
    digits between them, which covers both the 2018 and 2022 World Cup graphics.
    """

    def __init__(self, min_confidence: float = 0.3) -> None:
        self._min_confidence = min_confidence

    def parse(self, time: float, tokens: list[OcrToken]) -> ScoreReading | None:
        tokens = sorted((t for t in tokens if t.confidence >= self._min_confidence), key=lambda t: t.x)
        teams = [t for t in tokens if TEAM_CODE.match(t.text.strip())]
        for i, home in enumerate(teams):
            for away in teams[i + 1:]:
                if abs(home.y - away.y) > SAME_ROW_PIXELS:
                    continue
                digits = self._digits_between(tokens, home, away)
                if digits is not None:
                    return ScoreReading(
                        time=time,
                        home_code=home.text.strip(),
                        away_code=away.text.strip(),
                        home=digits[0],
                        away=digits[1],
                        clock_seconds=self._clock(tokens, home.y),
                    )
        return None

    @staticmethod
    def _digits_between(tokens: list[OcrToken], home: OcrToken, away: OcrToken) -> tuple[int, int] | None:
        between = [
            t.text.strip() for t in tokens
            if home.x < t.x < away.x and abs(t.y - home.y) <= SAME_ROW_PIXELS
        ]
        numbers = [s for s in between if SCORE_DIGITS.match(s)]
        if len(numbers) == 2:
            return int(numbers[0]), int(numbers[1])
        # OCR sometimes glues "1 0" into "10"; scores of 10+ are rare enough to read it as two digits
        if len(numbers) == 1 and len(numbers[0]) == 2:
            return int(numbers[0][0]), int(numbers[0][1])
        return None

    @staticmethod
    def _clock(tokens: list[OcrToken], row_y: float) -> int | None:
        for token in tokens:
            match = CLOCK.match(token.text.strip())
            if match and abs(token.y - row_y) <= SAME_ROW_PIXELS:
                return int(match.group(1)) * 60 + int(match.group(2))
        return None
