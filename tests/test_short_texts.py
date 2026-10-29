import json

from fshorts.branding.overlay import CaptionStyle, OverlaySpec, ShortOverlay
from fshorts.branding.rules import problems
from fshorts.branding.writer import ShortTextWriter
from fshorts.events.replay_events import TextGenerator
from fshorts.facts.model import GoalFact, MatchFacts, Player, Team
from fshorts.facts.sheet import MomentFacts, MomentFactsBuilder

FACTS = MatchFacts(
    Team("POR", "Portugal", [Player("Rui Patrício", "Rui Patrício", 1, "GK"),
                             Player("Cristiano Ronaldo", "Cristiano Ronaldo", 7, "CF"),
                             Player("Bernardo Silva", "Bernardo Silva", 11, "RW")]),
    Team("ESP", "Spain", [Player("David de Gea", "David de Gea", 1, "GK"), Player("Nacho", "Nacho", 4, "RB"),
                          Player("Isco", "Isco", 22, "AM"), Player("Sergio Ramos", "Sergio Ramos", 15, "CB"),
                          Player("David Silva", "David Silva", 21, "RW")]),
    [GoalFact("POR", "Ronaldo", "Cristiano Ronaldo", 4, 0, "pen."), GoalFact("ESP", "Nacho", "Nacho", 58),
     GoalFact("POR", "Ronaldo", "Cristiano Ronaldo", 88)],
)
SQUAD = {"rui", "patricio", "cristiano", "ronaldo", "bernardo", "silva", "david", "de", "gea", "nacho", "isco",
         "sergio", "ramos"}
BUILDER = MomentFactsBuilder(FACTS)


def test_goal_facts_come_from_the_match_not_the_commentary():
    nacho = BUILDER.goal(1, (1, 0), (1, 1), 58, "POR", "ESP")
    third = BUILDER.goal(2, (2, 2), (3, 2), 88, "POR", "ESP")

    assert (nacho.player, nacho.player_team, nacho.equaliser, nacho.nth_goal) == ("Nacho", "Spain", True, 1)
    assert (third.player, third.nth_goal, third.late, third.go_ahead) == ("Cristiano Ronaldo", 2, True, True)


def test_goal_name_is_dropped_when_facts_disagree_with_the_score_bug():
    # Our 2nd goal went to the home side, the facts say the 2nd goal was Spain's: trust neither name
    facts = BUILDER.goal(1, (1, 0), (2, 0), 58, "POR", "ESP")

    assert facts.player is None and facts.score_after == "2-0"


def test_save_named_after_the_keeper_is_his_save():
    keeper = BUILDER.chance("shot_saved", "De Gea", 30, "POR", "ESP")
    shooter = BUILDER.chance("shot_saved", "Ronaldo", 30, "POR", "ESP")

    assert (keeper.keeper, keeper.player) == ("De Gea", None)
    assert (shooter.player, shooter.keeper) == ("Cristiano Ronaldo", "De Gea")
    assert BUILDER.chance("shot_saved", "Silva", 30, "POR", "ESP").player is None


def test_rules_reject_wrong_names_and_unsupported_claims():
    nacho = BUILDER.goal(1, (1, 0), (1, 1), 58, "POR", "ESP")
    first = BUILDER.goal(0, (0, 0), (1, 0), 4, "POR", "ESP")
    save = BUILDER.chance("shot_saved", "Ronaldo", 30, "POR", "ESP")

    assert problems("Isco's shot! ⚽", nacho, SQUAD) == ["wrong player 'Isco'"]
    assert problems("Ramos saved! ⚽", save, SQUAD) == ["wrong player 'Ramos'"]
    assert problems("Nacho levels it 🤯", nacho, SQUAD) == []
    assert "unsupported 'again'" in problems("Ronaldo strikes again", first, SQUAD)
    assert problems("Ronaldo from the spot", first, SQUAD) == []
    assert "unsupported 'goal'" in problems("What a goal from Ronaldo", save, SQUAD)
    assert "unknown name 'Yi'" in problems("Saved by Wang Yi-chan 🤯", save, SQUAD)
    assert problems("Incredible save 🧤", save, SQUAD) == []
    assert "unsupported number 25" in problems("From 25 yards", save, SQUAD)
    assert "8 words" in problems("one two three four five six seven eight", save, SQUAD)


def test_rules_reject_shouting_grammar_and_the_wrong_team_leading():
    nacho = BUILDER.goal(1, (1, 0), (1, 1), 58, "POR", "ESP")
    third = BUILDER.goal(2, (2, 2), (3, 2), 88, "POR", "ESP")

    assert "shouting" in problems("CRISTIANO RONALDO HAT-TRICK!", third, SQUAD)
    assert problems("Ronaldo out of NOWHERE 🤯", third, SQUAD) == []
    assert "bad grammar 'a' before a vowel" in problems("Spain need a equaliser", nacho, SQUAD)
    assert "'lead' given to Portugal" in problems("Portugal lead…", MomentFacts("goal", "Portugal", "Spain", 60,
                                                                          player_team="Spain", go_ahead=True), SQUAD)
    assert problems("Spain looking for an equaliser…", nacho, SQUAD) == []
    assert "unsupported 'still'" in problems("The score… still 1-1", nacho, SQUAD)


def test_writer_never_repeats_a_line_in_one_match():
    facts = BUILDER.chance("shot_saved", "De Gea", 30, "POR", "ESP")
    answer = {"options": [{"format": "teaser", "line1": "Wait for it… 👀"},
                          {"format": "question", "line1": "How did he save this?! 🤯"}]}
    writer = ShortTextWriter(Scripted(answer), SQUAD)

    assert writer.write(facts).line1 == "Wait for it… 👀"
    assert writer.write(facts).line1 == "How did he save this?! 🤯"


class Scripted(TextGenerator):
    def __init__(self, answer: dict) -> None:
        self.answer = answer
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "```json\n" + json.dumps(self.answer) + "\n```"


def test_writer_keeps_the_first_supported_option():
    facts = BUILDER.goal(1, (1, 0), (1, 1), 58, "POR", "ESP")
    generator = Scripted({"options": [
        {"format": "label", "line1": "Isco's goal! ⚽", "line2": None},
        {"format": "two_beat", "line1": "Nacho from the edge…", "line2": "Off the post and in 🤯"},
        {"format": "teaser", "line1": "Wait for Nacho 👀", "line2": None},
    ], "title": "Nacho stunner! Portugal vs Spain ⚽"})

    text = ShortTextWriter(generator, SQUAD).write(facts)

    # The two-beat punchline is too long and claims a post, so the teaser wins
    assert (text.format, text.line1, text.line2) == ("teaser", "Wait for Nacho 👀", None)
    assert text.title == "Nacho stunner! Portugal vs Spain ⚽" and text.player == "Nacho"
    assert '"player": "Nacho"' in generator.prompts[0]


def test_writer_falls_back_when_nothing_passes():
    facts = BUILDER.chance("shot_saved", "De Gea", 30, "POR", "ESP")

    text = ShortTextWriter(Scripted({"options": [{"format": "label", "line1": "Ramos blocks it"}]}), SQUAD).write(facts)

    assert text.line1 == "De Gea says no ✋" and "Portugal vs Spain" in text.title


def test_overlay_timing_per_format():
    style = CaptionStyle(size=40, y_share=0.7, label_share=0.6)
    label = ShortOverlay(OverlaySpec("label", "Iconic.", None, moment=12.0, duration=16.0), (1080, 1920), style)
    teaser = ShortOverlay(OverlaySpec("teaser", "Wait for it", None, 12.0, 16.0), (1080, 1920), style)
    beat = ShortOverlay(OverlaySpec("two_beat", "Try to stop him", "Impossible", 12.0, 16.0), (1080, 1920), style)

    assert label.windows() == [("line1", 0.0, 9.6)]
    assert teaser.windows() == [("line1", 0.0, 11.75)]
    assert beat.windows() == [("line1", 0.0, 11.75), ("line2", 12.0, 16.0)]


def test_replay_part_has_no_text():
    spec = OverlaySpec("two_beat", "Try to stop him", "Impossible", 12.0, 16.0).for_replay(6.0)

    assert ShortOverlay(spec, (1080, 1920)).windows() == []


def test_moment_facts_list_only_what_is_known():
    facts = MomentFacts("near_miss", "Portugal", "Spain", 35)

    assert facts.to_dict() == {"kind": "near_miss", "home": "Portugal", "away": "Spain", "minute": 35}


def test_compare_pairs_versions_by_clip():
    from fshorts.studio.ratings import ShortRating, compare

    old = {"a": ShortRating("a", 3, kind="goal"), "b": ShortRating("b", 2, kind="chance"),
           "c": ShortRating("c", 4, kind="chance")}
    new = {"a": ShortRating("a", 5, kind="goal"), "b": ShortRating("b", 2, kind="chance")}

    rows = {r.kind: r for r in compare(old, new)}

    assert (rows["goal"].old_stars, rows["goal"].new_stars, rows["goal"].better) == (3, 5, 1)
    assert (rows["all"].pairs, rows["all"].worse) == (2, 0) and "chance" in rows


def test_replay_angle_is_a_run_of_play_views_even_without_a_scene_cut():
    from fshorts.broadcast import BroadcastTimeline
    from fshorts.clipping.shorts import ReplayAnglePicker

    # 2 fps: close-ups, a wide run with one misread logo frame, then goal-mouth until the end
    views = ["close"] * 8 + ["wide"] * 6 + ["logo"] + ["wide"] * 5 + ["goalmouth"] * 10 + ["close"] * 4
    timeline = BroadcastTimeline(2.0, (False,) * len(views), tuple(views))

    assert timeline.runs(0, 17, ("wide", "goalmouth")) == [(4.0, 15.0)]
    assert ReplayAnglePicker(timeline).pick(0, 17, cuts=[10.0]) == (10.25, 14.75)
    assert ReplayAnglePicker(BroadcastTimeline(2.0, (False,) * 8, ("close",) * 8)).pick(0, 4, []) is None


def test_writer_retries_with_the_reasons_then_uses_the_story():
    third = BUILDER.goal(2, (2, 2), (3, 3), 88, "POR", "ESP")
    generator = Scripted({"options": [{"format": "label", "line1": "CRISTIANO RONALDO HAT-TRICK!"}]})

    text = ShortTextWriter(generator, SQUAD).write(third)

    assert len(generator.prompts) == 2 and "shouting" in generator.prompts[1]
    # In this fixture it is his second goal, a 3-3 equaliser
    assert text.line1 == "Cristiano Ronaldo levels it 🤯"


def test_rules_reject_restarts_and_teasing_punchlines():
    save = BUILDER.chance("shot_saved", "Ronaldo", 30, "POR", "ESP")
    answer = {"options": [{"format": "two_beat", "line1": "Spain looking for a chance", "line2": "Wait for it… 👀"},
                          {"format": "label", "line1": "Wait for the throw-in"},
                          {"format": "label", "line1": "Incredible save 🧤"}]}

    assert "unsupported 'throw'" in problems("Wait for the throw-in", save, SQUAD)
    assert ShortTextWriter(Scripted(answer), SQUAD).write(save).line1 == "Incredible save 🧤"


def test_names_in_capitals_and_save_titles():
    from fshorts.branding.writer import fallback_title

    save = BUILDER.chance("shot_saved", "Ronaldo", 30, "POR", "ESP")

    assert "name in capitals 'RONALDO'" in problems("RONALDO takes the ball", save, SQUAD)
    assert fallback_title(save).startswith("What a save De Gea!")


def test_wrapped_caption_lines_are_balanced():
    from fshorts.branding.text import TextPainter

    painter = TextPainter(56)
    text = "Mbappé's second goal of the match"
    lines = painter.wrap(text, painter.width(text) - 40)

    assert lines == ["Mbappé's second", "goal of the match"]
