"""Read-only category evaluation for #95958774220587008.

Run from the repo root with:
    uv run --with pyyaml --with yt-dlp -m scripts.evaluate_categories

Uses index titles and the retained topic tags from report frontmatter. Reports
persist only five slugged tags, so this cannot recreate original yt-dlp inputs.
Stored assignments are the operational baseline, never ground truth. Collection
labels are evaluation-only and are not passed to get_category(). No files are
written, no metadata fetched, and no existing report is recategorized.
"""

import argparse
from collections import Counter
import json
from pathlib import Path

import yaml

from scripts.librarian import get_category


# Fixed before implementation, from collection treatments. Daisy is a source
# collection covering multiple creative topics; this measures family agreement,
# not exact per-video accuracy or held-out generalization.
COLLECTION_CATEGORIES = {
    "jev": {"ai_automation"},
    "self-help": {"self_improvement"},
    "investment": {"finance"},
    "geopolitics": {"geopolitics"},
    "lance-breitstein": {"finance"},
    "agentic-work": {"agentic_workflows"},
    "cults": {"politics_power"},
    "daisy-studios": {"animation_video", "image_design", "audio_music", "content_strategy"},
}


def evaluate(index_path: Path) -> dict:
    """Compare stored and predicted categories; fail on unreadable evidence."""
    entries = yaml.safe_load(index_path.read_text(encoding="utf-8"))["entries"]
    stored, predicted = Counter(), Counter()
    agreement = {"stored": 0, "predicted": 0, "scored": 0}
    per_collection = {}
    for entry in entries:
        report = (index_path.parent.parent / entry["filepath"]).read_text(encoding="utf-8")
        frontmatter = yaml.safe_load(report.split("---", 2)[1]) if report.startswith("---\n") else {}
        tags = [tag.removeprefix("topic/") for tag in (frontmatter or {}).get("tags", [])
                if tag.startswith("topic/")]
        category = get_category(entry["title"], tags)["id"]
        stored[entry["category_id"]] += 1
        predicted[category] += 1
        if collection := entry.get("collection"):
            # An unknown collection must get an explicit rubric, not disappear
            # silently from the denominator as the library grows.
            expected = COLLECTION_CATEGORIES[collection]
            counts = per_collection.setdefault(collection, {"stored": 0, "predicted": 0, "scored": 0})
            for target in (agreement, counts):
                target["scored"] += 1
                target["stored"] += entry["category_id"] in expected
                target["predicted"] += category in expected
    return {"entries": len(entries), "stored": dict(stored), "predicted": dict(predicted),
            "agreement": agreement, "per_collection": per_collection}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=Path("library/index.yaml"))
    args = parser.parse_args()
    print(json.dumps(evaluate(args.index), indent=2, sort_keys=True))
