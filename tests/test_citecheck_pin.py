"""The pinned citecheck keeps both halves of a prose dash quotable (v0.2.1)."""
from citecheck import quote_in


def test_prose_dash_after_a_number_keeps_both_halves():
    source = "Employment reached 450—double last year."
    assert quote_in("Employment reached 450", source)
    assert quote_in("double last year", source)


def test_a_dropped_minus_is_not_a_match():
    assert not quote_in("Amount: $24.99", "Amount: -$24.99")
