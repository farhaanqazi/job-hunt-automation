from jobhunt.reports.console import format_remote_label


def test_format_remote_label_humanizes_remote_category():
    assert format_remote_label("india_remote") == "India remote"
    assert format_remote_label("global_remote") == "Global remote"


def test_format_remote_label_passes_through_unknown_value():
    assert format_remote_label("something_else") == "something_else"
