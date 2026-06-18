from jobhunt.web.presentation import reason_label, strip_html


def test_strip_html_removes_tags_and_keeps_text():
    html = '<p style="min-height: 1.5em;">Here at <strong>Clerky</strong>, we build software.</p>'
    out = strip_html(html)
    assert "<p" not in out
    assert "<strong>" not in out
    assert "Here at Clerky, we build software." in out


def test_strip_html_renders_list_items():
    out = strip_html("<ul><li>One</li><li>Two</li></ul>")
    assert "• One" in out
    assert "• Two" in out


def test_strip_html_handles_none():
    assert strip_html(None) == ""


def test_reason_label_humanizes_prefixes():
    assert reason_label("strong: backend") == "Backend (strong)"
    assert reason_label("learning: aws") == "Aws (to learn)"
    assert reason_label("excluded keyword: onsite") == "Excluded: onsite"
    assert reason_label("remote match") == "Remote match"
