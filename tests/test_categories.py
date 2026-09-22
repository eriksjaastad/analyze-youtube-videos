from pathlib import Path
import random

import pytest
import yaml

from scripts.librarian import get_category
from scripts.evaluate_categories import evaluate


# Four individually named failures in the card, plus the Fat Loss Scientist
# entry illustrating its AI bucket collapse. Full reports remain unversioned.
REGRESSIONS = [
    ("Jev is incredible", ["web-development", "typescript", "javascript", "react"], "ai_automation"),
    ("Why We Made Jev — Diogo Almeida, TypeSafe Co-founder & CEO", [], "ai_automation"),
    ("Why Wall Street is Ignoring Big Tech's Debt", ["ai", "finance", "trading"], "finance"),
    ("52 Minute Risk Management Masterclass from a $100,000,000 Trader", ["strategy"], "finance"),
    ("Fat Loss Scientist: It’s Easy To Lose Weight, But Here’s Why You WON’T Do It! | Dr Andy Galpin",
     ["ai", "podcast"], "health_diet"),
]


@pytest.mark.parametrize("title,tags,expected", REGRESSIONS)
def test_card_regressions(title, tags, expected):
    assert get_category(title, tags)["id"] == expected


@pytest.mark.parametrize("title,tags,expected", [
    ("AI", [], "ai_automation"),
    ("Use Local LLMs Already!", [], "ai_automation"),
    ("AI animation tutorial", ["ai", "agent", "llm", "automation"], "animation_video"),
    ("Midjourney character design", ["ai"], "image_design"),
    ("Text-to-speech tools", ["ai", "video generators"], "audio_music"),
    ("AI content strategy", [], "content_strategy"),
    ("Day Trading Strategy", ["youtube", "strategy"], "finance"),
    ("Geopolitics of AI drone warfare", ["ai"], "geopolitics"),
    ("Python software engineering", ["ai"], "development"),
    ("What does this do?", [], "miscellaneous"),
    ("A chair in a warehouse", [], "miscellaneous"),
    ("", [], "miscellaneous"),
    ("Something entirely new", ["wall", "street"], "miscellaneous"),
    ("ＷＡＬＬ—ＳＴＲＥＥＴ", [], "finance"),
])
def test_subject_and_normalization(title, tags, expected):
    assert get_category(title, tags)["id"] == expected


def test_order_and_repetition_cannot_change_classification(tmp_path, monkeypatch):
    config = yaml.safe_load(Path("config/categories.yaml").read_text())
    cases = REGRESSIONS + [
        ("AI animated character", ["ai", "character"], "animation_video"),
        ("Claude Code Task System: ANTI-HYPE Agentic Coding", [], "agentic_workflows"),
    ]
    monkeypatch.chdir(tmp_path)
    Path("config").mkdir()
    for seed in range(6):
        random.Random(seed).shuffle(config["categories"])
        Path("config/categories.yaml").write_text(yaml.safe_dump(config))
        for title, tags, expected in cases:
            assert get_category(title, tags)["id"] == expected
            assert get_category(title, tags * 20)["id"] == expected
            assert get_category(title + " " + title, tags)["id"] == expected


def test_equal_evidence_abstains_and_lists_still_work(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("config").mkdir()
    config = {"categories": [
        {"id": "a", "name": "A", "keywords": ["shared", "unique"]},
        {"id": "b", "name": "B", "keywords": {"shared": 1}},
    ], "default_category": {"id": "fallback", "name": "Fallback"}}
    for categories in (config["categories"], list(reversed(config["categories"]))):
        config["categories"] = categories
        Path("config/categories.yaml").write_text(yaml.safe_dump(config))
        assert get_category("shared", []) == config["default_category"]
        assert get_category("unique", []) == {"id": "a", "name": "A"}


def test_nested_keyword_is_not_double_counted(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("config").mkdir()
    config = {"categories": [
        {"id": "a", "name": "A", "keywords": {"art": 1, "modern art": 2}},
        {"id": "b", "name": "B", "keywords": {"photography": 2}},
    ]}
    Path("config/categories.yaml").write_text(yaml.safe_dump(config))
    assert get_category("modern-art photography", [])["id"] == "miscellaneous"


def test_evaluation_uses_collections_only_for_scoring_and_preserves_files(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    report = library / "report.md"
    report.write_text("---\ntags: [p/analyze-youtube-videos, topic/ai]\n---\nReport untouched.\n")
    index = library / "index.yaml"
    entry = {"title": "Wall Street debt", "collection": "jev", "category_id": "ai_automation",
             "filepath": "library/report.md"}
    index.write_text(yaml.safe_dump({"entries": [entry]}))
    before = {p: p.read_bytes() for p in library.iterdir()}
    result = evaluate(index)
    assert result["predicted"] == {"finance": 1}
    assert result["agreement"] == {"stored": 1, "predicted": 0, "scored": 1}
    assert {p: p.read_bytes() for p in library.iterdir()} == before
    entry["collection"] = "investment"
    index.write_text(yaml.safe_dump({"entries": [entry]}))
    result = evaluate(index)
    assert result["predicted"] == {"finance": 1}
    assert result["agreement"] == {"stored": 0, "predicted": 1, "scored": 1}
