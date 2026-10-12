"""Loads the built-in sample screenshots and their pre-computed (seeded) results."""
from __future__ import annotations

import json
from pathlib import Path

SAMPLES_DIR = Path(__file__).parent / "samples"


def load_samples() -> list[dict]:
    """Each sample: {id, title, path, result}. Empty list if the samples folder is missing."""
    seeded_file = SAMPLES_DIR / "seeded_results.json"
    if not seeded_file.exists():
        return []
    seeded = json.loads(seeded_file.read_text(encoding="utf-8"))
    samples = []
    for sample_id, meta in seeded.items():
        png = SAMPLES_DIR / f"{sample_id}.png"
        if png.exists():
            samples.append({"id": sample_id, "title": meta["title"], "path": png, "result": meta["result"]})
    return samples
