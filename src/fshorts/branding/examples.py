"""Real captions of the most viewed in-game Shorts of big channels (docs/research/reference_captions.json).

Grouped by the moment they caption and by format; the writer shows the model each group.
Two-beat examples are "line1 → line2". Examples that state what we can never know from a broadcast
(distances, nutmegs, debuts) are left out so the model does not copy them.
"""

EXAMPLES = {
    "goal": {
        "label": ["Iconic.", "Pure chaos", "This Paris team move 👏", "Chaotic second goal 🤣",
                  "Real Madrid's comeback 😮‍💨", "A 10/10 assist 🔥", "The Jeremy Doku special™",
                  "This Galatasaray move! 🔥", "Every watch gets better"],
        "teaser": ["The score… 👀", "Wait for Doué's reaction 🤣", "Incredible pass incoming"],
        "question": ["Most satisfying finish ever? 😮‍💨", "How satisfying is this pass? 😍"],
        "two_beat": ["Nottingham Forest are looking for an equaliser… → Konsa said 🙅",
                     "Try to take the ball off João Neves → Impossible"],
    },
    "chance": {
        "label": ["Sommer foot save 🤯", "Trey Nyoni said NO!", "Zion Suzuki appeared out of NOWHERE…",
                  "An INCREDIBLE Ronald Araujo clearance", "Pure PASSION from Declan Rice"],
        "teaser": ["Wait for it… 👀", "Wait for the save 🧤", "Incredible pass incoming"],
        "question": ["How close was this from David Raya?", "How did he save this?! 🤯"],
        "two_beat": ["Nottingham Forest are looking for an equaliser… → Konsa said 🙅",
                     "Zion Suzuki can do EVERYTHING → Save 🧤"],
    },
    "skill": {
        "label": ["Harry Kane's goal-kick 🤯", "Doué VS Lamine", "Footballing lesson from Sergio Busquets",
                  "Eyes on Messi", "Pedri 🪄", "Florian Wirtz bringing the game to life", "99 strength 💪"],
        "teaser": ["Wait for Mbappé's pace 🤯", "Wait for Verratti's WTF moment…", "Bouaddi magic in 5… 3… 2…"],
        "question": ["How satisfying is this pass? 😍"],
        "two_beat": ["Try to take the ball off João Neves → Impossible",
                     "Dominik Szoboszlai's recovery speed → Here he comes!"],
    },
}
