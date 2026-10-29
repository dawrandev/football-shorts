from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from fshorts.broadcast import Replay
from fshorts.events.commentary import Word

# What a replayed moment can be; the first group becomes chance clips
CHANCE_KINDS = ("shot_saved", "shot_off_target", "shot_blocked", "woodwork", "near_miss")
KINDS = CHANCE_KINDS + (
    "goal_recap", "penalty_awarded", "skill", "foul", "card", "offside", "corner", "injury", "other",
)

# What the model sometimes writes instead of leaving the player empty
NOT_A_NAME = {"", "null", "none", "unknown", "he", "she", "him", "they"}

PROMPT = """You label one replayed moment of a football match from the TV commentary around it.
Times are seconds relative to the live action the replay shows (0 = the action).
Lines marked [replay] were spoken while the replay was on screen.
The score did NOT change at this moment: it is not a goal.

Commentary:
{lines}

Answer with JSON only:
{{"kind": one of {kinds},
 "player": the one player at the centre of it, as the commentator names him (a person, never a team), or null,
 "summary": at most 12 words on what happened}}

Rules:
- "goal_recap" only when the commentator clearly says we are seeing an earlier goal again
  ("let's see that goal again", "the first goal"). Talk about goals or the score alone is not enough.
- A shot that is saved, goes wide/over, is blocked or hits the post counts as a shot kind even if the
  commentator mostly talks about something else afterwards.
- "skill" only for an individual dribble or trick that beats an opponent and does not end in a shot.
  A run that ends with a shot is a shot kind."""


@dataclass(frozen=True)
class ReplayEvent:
    replay: Replay
    kind: str
    player: str | None
    summary: str
    recap: bool = False   # the replay reuses footage aired earlier (a recap, not a new moment)

    @property
    def is_chance(self) -> bool:
        return self.kind in CHANCE_KINDS

    @property
    def is_skill(self) -> bool:
        # A skill clip is about one player; without a name it is not worth a clip
        return self.kind == "skill" and self.player is not None

    def to_dict(self) -> dict:
        return {"replay": self.replay.to_dict(), "kind": self.kind, "player": self.player, "summary": self.summary,
                "recap": self.recap}

    @classmethod
    def from_dict(cls, raw: dict) -> ReplayEvent:
        return cls(Replay.from_dict(raw["replay"]), raw["kind"], raw["player"], raw["summary"], raw.get("recap", False))


class TextGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        ...


class QwenGenerator(TextGenerator):
    """Local Qwen3 (Apache-2.0) through transformers; thinking mode only when asked for."""

    def __init__(self, model_name: str = "Qwen/Qwen3-8B", max_new_tokens: int = 120, thinking: bool = False) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch.bfloat16, device_map="cuda")
        self._max_new_tokens = max_new_tokens
        self._thinking = thinking

    def generate(self, prompt: str) -> str:
        text = self._tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True,
            enable_thinking=self._thinking,
        )
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)
        with self._torch.no_grad():
            output = self._model.generate(**inputs, max_new_tokens=self._max_new_tokens, do_sample=False)
        answer = self._tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return answer.split("</think>")[-1]


class ReplayEventClassifier:
    """Asks a language model what each replay shows, from the commentary before and during it."""

    def __init__(self, generator: TextGenerator, before: float = 25.0, after: float = 8.0) -> None:
        self._generator = generator
        self._before = before
        self._after = after

    def classify(self, replays: list[Replay], words: list[Word]) -> list[ReplayEvent]:
        return [self._classify(r, words) for r in replays]

    def prompt(self, replay: Replay, words: list[Word]) -> str:
        zero = replay.event if replay.event is not None else replay.start
        lines, current, mark = [], [], None
        for word in words:
            if not zero - self._before <= word.start <= replay.end + self._after:
                continue
            tag = " [replay]" if replay.start <= word.start < replay.end else ""
            if current and (tag != mark or current[-1].text.endswith((".", "!", "?"))):
                lines.append(self._line(current, zero, mark))
                current = []
            current.append(word)
            mark = tag
        if current:
            lines.append(self._line(current, zero, mark))
        return PROMPT.format(lines="\n".join(lines) or "(silence)", kinds=", ".join(KINDS))

    @staticmethod
    def _line(words: list[Word], zero: float, tag: str) -> str:
        return f"[{words[0].start - zero:+.0f}s]{tag} {' '.join(w.text for w in words)}"

    def _classify(self, replay: Replay, words: list[Word]) -> ReplayEvent:
        answer = self._parse(self._generator.generate(self.prompt(replay, words)))
        kind = answer.get("kind") if answer.get("kind") in KINDS else "other"
        player = str(answer.get("player") or "").strip()
        if player.lower() in NOT_A_NAME:
            player = ""
        return ReplayEvent(replay, kind, player or None, str(answer.get("summary") or ""))

    @staticmethod
    def _parse(text: str) -> dict:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        try:
            return json.loads(match.group(0)) if match else {}
        except json.JSONDecodeError:
            return {}


class CachedReplayEventClassifier:
    def __init__(self, inner: ReplayEventClassifier, cache: Path) -> None:
        self._inner = inner
        self._cache = cache

    def classify(self, replays: list[Replay], words: list[Word]) -> list[ReplayEvent]:
        if self._cache.is_file():
            return [ReplayEvent.from_dict(e) for e in json.loads(self._cache.read_text(encoding="utf-8"))]
        events = self._inner.classify(replays, words)
        self._cache.write_text(json.dumps([e.to_dict() for e in events], ensure_ascii=False, indent=1), encoding="utf-8")
        return events
