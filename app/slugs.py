from nanoid import generate as nano
from slugify import slugify

SUFFIX_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
SUFFIX_LEN = 4
BASE_MAX = 40


def generate_slug(brand_name: str) -> str:
    base = slugify(brand_name or "", max_length=BASE_MAX, word_boundary=True) or "site"
    suffix = nano(SUFFIX_ALPHABET, SUFFIX_LEN)
    return f"{base}-{suffix}"
