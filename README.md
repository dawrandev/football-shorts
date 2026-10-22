# football-shorts

Full football match video in, vertical (1080x1920) highlight Shorts out: goals and big chances are detected automatically, clipped, reframed to follow the ball and branded with GOAL / team / score overlays.

Plan and milestones: [docs/PLAN.md](docs/PLAN.md). Research: [docs/research/](docs/research/).

## Setup (Windows, RTX 5090)

Requires FFmpeg with NVENC on `PATH` and the Python 3.12 venv with PyTorch cu130.

```powershell
C:\Users\dawra\ai-env\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

## Usage

```powershell
fshorts probe data\matches\match.mp4
```

## Test matches

Put full match files in `data/matches/` (ignored by git). For each one write the hand-labelled answers to `tests/ground_truth/<match>.json` using `example.json` as the template.
