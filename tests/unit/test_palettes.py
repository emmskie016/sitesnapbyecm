import pytest

from app.palettes import PALETTE_HINTS, get_palette


def test_each_archetype_has_four_palettes():
    for arch in ("service", "hospitality", "portfolio"):
        assert len(PALETTE_HINTS[arch]) == 4


def test_palette_returns_full_token_set():
    p = get_palette("service", "warm-earth")
    expected_keys = {"primary", "accent", "neutral_bg", "neutral_surface", "ink", "ink_soft"}
    assert set(p.keys()) == expected_keys
    for v in p.values():
        assert v.startswith("#") and len(v) == 7


def test_palette_unknown_hint_falls_back_to_first():
    p_first = get_palette("service", PALETTE_HINTS["service"][0])
    p_unknown = get_palette("service", "nope-not-a-hint")
    assert p_first == p_unknown


def test_palette_unknown_archetype_raises():
    with pytest.raises(KeyError):
        get_palette("nonsense", "warm-earth")
