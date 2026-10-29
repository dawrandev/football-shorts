from fshorts.facts.model import MatchFacts
from fshorts.facts.wiki import parse_match

PAGE = """Intro text.
<section begin=b2 />{{Football box
|team1={{fb-rt|POR|1974}}
|score=3–3
|team2={{#invoke:flagg|main|unpe|avar=fb|ESP}}
|goals1=
*[[Cristiano Ronaldo|Ronaldo]] {{goal|4|pen.|44||88}}
|goals2=
*[[Diego Costa|Costa]] {{goal|24||55}}
*[[Nacho (footballer, born 1990)|Nacho]] {{goal|58}}
*[[Pepe (footballer, born 1983)|Pepe]] {{goal|90+2|o.g.}}
|stadium=[[Fisht Olympic Stadium]]
}}
{| style="font-size:90%" cellspacing="0" cellpadding="0"
|GK ||'''1''' ||[[Rui Patrício]]
|CB ||'''3''' ||[[Pepe (footballer, born 1983)|Pepe]]
|RW ||'''11'''||[[Bernardo Silva]] || || {{suboff|69}}
|CF ||'''7''' ||[[Cristiano Ronaldo]] ([[Captain (association football)|c]])
|colspan=3|'''Substitutions:'''
|FW ||'''9''' ||[[André Silva (footballer, born 1995)|André Silva]] || || {{subon|80}}
|}
{| style="font-size:90%; margin:auto" cellspacing="0" cellpadding="0"
|GK ||'''1''' ||[[David de Gea]]
|RB ||'''4''' ||[[Nacho (footballer, born 1990)|Nacho]]
|RW ||'''21'''||[[David Silva]]
|CF ||'''19'''||[[Diego Costa]]
|}
<section begin=b3 />{{Football box
|team1={{fb-rt|IRN}}
|team2={{fb|ESP}}
}}
"""


def facts() -> MatchFacts:
    return parse_match(PAGE, "POR", "ESP", "Portugal", "Spain")


def test_line_ups_and_goals_come_from_the_match_box():
    f = facts()

    assert [p.name for p in f.home.players] == ["Rui Patrício", "Pepe", "Bernardo Silva", "Cristiano Ronaldo",
                                                "André Silva"]
    assert not f.home.players[-1].starter and f.home.players[0].is_goalkeeper
    assert [(g.team, g.scorer, g.minute, g.note) for g in f.goals] == [
        ("POR", "Ronaldo", 4, "pen."), ("ESP", "Costa", 24, ""), ("POR", "Ronaldo", 44, ""),
        ("ESP", "Costa", 55, ""), ("ESP", "Nacho", 58, ""), ("POR", "Ronaldo", 88, ""), ("ESP", "Pepe", 90, "o.g."),
    ]
    assert f.goals[-1].added == 2 and f.goals[-1].own_goal


def test_names_resolve_to_one_player_or_none():
    f = facts()

    assert f.resolve("Patricio").player.name == "Rui Patrício"
    assert f.resolve("de gea").player.is_goalkeeper
    assert f.resolve("Costa").team == "ESP"
    assert f.resolve("Silva") is None             # three Silvas on the pitch
    assert f.resolve("Bernardo").player.number == 11
    assert f.resolve("Isco") is None              # not in this line-up
    assert f.resolve("the goalkeeper") is None


def test_goal_counts_per_player():
    f = facts()

    assert f.goals_by("Cristiano Ronaldo", upto=0) == 1
    assert f.goals_by("Cristiano Ronaldo", upto=5) == 3
    assert f.goals_by("Pepe", upto=6) == 0        # an own goal is not his goal


def test_facts_round_trip(tmp_path):
    f = facts()
    f.save(tmp_path / "facts.json")

    assert MatchFacts.load(tmp_path / "facts.json") == f
