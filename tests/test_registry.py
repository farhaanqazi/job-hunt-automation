from jobhunt.sources.registry import load_source_catalog


def test_load_source_catalog_returns_typed_metadata():
    catalog = load_source_catalog()
    assert set(catalog) >= {"remotive", "adzuna", "greenhouse", "lever", "arbeitnow"}
    remotive = catalog["remotive"]
    assert remotive.source_id == "remotive"
    assert remotive.requires_attribution is True
    assert remotive.redistribution_allowed is False
