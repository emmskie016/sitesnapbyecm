import re

from app.slugs import generate_slug


def test_slug_is_kebab_case_with_suffix():
    s = generate_slug("Bloom Florist!")
    assert re.fullmatch(r"bloom-florist-[a-z0-9]{4}", s)


def test_slug_handles_unicode_and_emoji():
    s = generate_slug("Cafe Ñoño 🌮")
    # python-slugify ASCII-folds Ñ→N, drops emoji
    assert s.startswith("cafe-nono-") and re.fullmatch(r"cafe-nono-[a-z0-9]{4}", s)


def test_slug_empty_brand_falls_back_to_site():
    s = generate_slug("   ")
    assert re.fullmatch(r"site-[a-z0-9]{4}", s)


def test_slug_truncates_long_brand():
    long = "A" * 200
    s = generate_slug(long)
    base, _, suffix = s.rpartition("-")
    assert len(base) <= 40
    assert re.fullmatch(r"[a-z0-9]{4}", suffix)
