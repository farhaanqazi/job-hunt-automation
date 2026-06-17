from types import SimpleNamespace

from jobhunt.reports.export_csv import rows_to_csv_text


def make_row():
    return SimpleNamespace(
        id=1,
        fit_score=90,
        remote_category="global_remote",
        company="Example",
        title="Python Engineer",
        source_id="remotive",
        source_url="https://example.com/job",
        attribution="Remotive",
        status="found",
    )


def test_rows_to_csv_text_includes_source_url_and_attribution():
    text = rows_to_csv_text([make_row()])

    assert "source_url" in text
    assert "https://example.com/job" in text
    assert "Remotive" in text


def test_rows_to_csv_text_emits_header_only_for_empty_rows():
    text = rows_to_csv_text([])
    assert text.splitlines()[0].startswith("id,fit_score")
