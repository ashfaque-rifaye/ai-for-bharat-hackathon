"""Tests for seed scheme data integrity."""

import json
import os
import pytest
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "infrastructure" / "seed-data" / "schemes"

REQUIRED_FIELDS = ["schemeId", "name", "description", "category", "eligibility"]
VALID_CATEGORIES = {"agriculture", "housing", "healthcare", "finance", "education", "food", "energy", "savings", "insurance"}
REQUIRED_LANGUAGES = {"en", "hi"}


class TestSeedSchemeData:
    @pytest.fixture
    def scheme_files(self):
        return sorted(SEED_DIR.glob("*.json"))

    def test_seed_dir_exists(self):
        assert SEED_DIR.exists(), f"Seed directory not found: {SEED_DIR}"

    def test_at_least_10_schemes(self, scheme_files):
        assert len(scheme_files) >= 10, f"Expected 10+ schemes, found {len(scheme_files)}"

    def test_all_files_valid_json(self, scheme_files):
        for f in scheme_files:
            data = json.loads(f.read_text(encoding="utf-8"))
            assert isinstance(data, dict), f"{f.name}: Root should be a dict"

    def test_required_fields_present(self, scheme_files):
        for f in scheme_files:
            data = json.loads(f.read_text(encoding="utf-8"))
            for field in REQUIRED_FIELDS:
                assert field in data, f"{f.name}: Missing field '{field}'"

    def test_valid_category(self, scheme_files):
        for f in scheme_files:
            data = json.loads(f.read_text(encoding="utf-8"))
            cat = data.get("category", "")
            assert cat in VALID_CATEGORIES, f"{f.name}: Invalid category '{cat}'"

    def test_multilingual_names(self, scheme_files):
        for f in scheme_files:
            data = json.loads(f.read_text(encoding="utf-8"))
            name = data.get("name", {})
            for lang in REQUIRED_LANGUAGES:
                assert lang in name, f"{f.name}: Missing '{lang}' in name"
                assert len(name[lang]) > 0, f"{f.name}: Empty name for '{lang}'"

    def test_scheme_ids_unique(self, scheme_files):
        ids = []
        for f in scheme_files:
            data = json.loads(f.read_text(encoding="utf-8"))
            ids.append(data["schemeId"])
        assert len(ids) == len(set(ids)), f"Duplicate scheme IDs found: {[x for x in ids if ids.count(x) > 1]}"

    def test_scheme_ids_match_filenames(self, scheme_files):
        for f in scheme_files:
            data = json.loads(f.read_text(encoding="utf-8"))
            stem_pattern = f.stem.upper().replace("_", "-")
            scheme_id = data["schemeId"]
            assert scheme_id.startswith(stem_pattern), \
                f"{f.name}: schemeId '{scheme_id}' doesn't start with '{stem_pattern}'"

    def test_eligibility_has_rules(self, scheme_files):
        for f in scheme_files:
            data = json.loads(f.read_text(encoding="utf-8"))
            elig = data.get("eligibility", {})
            assert len(elig) > 0, f"{f.name}: Eligibility rules are empty"
