from pathlib import Path

import yaml

from jobhunt.sources.base import SourceMetadata


def test_source_catalog_contains_required_v1_sources():
    data = yaml.safe_load(Path("config/source_catalog.yaml").read_text(encoding="utf-8"))
    sources = data["sources"]
    assert {"remotive", "adzuna", "greenhouse", "lever", "arbeitnow"}.issubset(sources)


def test_sources_do_not_claim_to_be_open_source():
    data = yaml.safe_load(Path("config/source_catalog.yaml").read_text(encoding="utf-8"))
    for source_id, source in data["sources"].items():
        metadata = SourceMetadata(source_id=source_id, **source)
        assert metadata.source_code_license == "closed"
        assert metadata.redistribution_allowed is False
