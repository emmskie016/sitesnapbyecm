"""Hand-curated palettes per archetype. 4 per archetype × 3 archetypes = 12 visual identities.

Hex values are picked, not LLM-generated, to guarantee a tasteful baseline.
"""

PALETTES: dict[str, dict[str, dict[str, str]]] = {
    "service": {
        "warm-earth": {
            "primary": "#8B5A3C",
            "accent": "#D4A574",
            "neutral_bg": "#FAF6F1",
            "neutral_surface": "#FFFFFF",
            "ink": "#2A1F18",
            "ink_soft": "#5C4A3D",
        },
        "cool-modern": {
            "primary": "#1E3A8A",
            "accent": "#38BDF8",
            "neutral_bg": "#F8FAFC",
            "neutral_surface": "#FFFFFF",
            "ink": "#0F172A",
            "ink_soft": "#475569",
        },
        "bold-vibrant": {
            "primary": "#9333EA",
            "accent": "#F59E0B",
            "neutral_bg": "#FAFAFA",
            "neutral_surface": "#FFFFFF",
            "ink": "#18181B",
            "ink_soft": "#52525B",
        },
        "muted-elegant": {
            "primary": "#374151",
            "accent": "#A78BFA",
            "neutral_bg": "#F9FAFB",
            "neutral_surface": "#FFFFFF",
            "ink": "#111827",
            "ink_soft": "#4B5563",
        },
    },
    "hospitality": {
        "warm-earth": {
            "primary": "#7C2D12",
            "accent": "#F59E0B",
            "neutral_bg": "#FEF8F0",
            "neutral_surface": "#FFFFFF",
            "ink": "#27150C",
            "ink_soft": "#6B4226",
        },
        "cool-modern": {
            "primary": "#0F766E",
            "accent": "#FBBF24",
            "neutral_bg": "#F0FDFA",
            "neutral_surface": "#FFFFFF",
            "ink": "#042F2E",
            "ink_soft": "#0D5F58",
        },
        "bold-vibrant": {
            "primary": "#DC2626",
            "accent": "#FACC15",
            "neutral_bg": "#FFFBEB",
            "neutral_surface": "#FFFFFF",
            "ink": "#1C1917",
            "ink_soft": "#57534E",
        },
        "muted-elegant": {
            "primary": "#1F2937",
            "accent": "#D4A574",
            "neutral_bg": "#F4F1EC",
            "neutral_surface": "#FFFFFF",
            "ink": "#111827",
            "ink_soft": "#4B5563",
        },
    },
    "portfolio": {
        "warm-earth": {
            "primary": "#451A03",
            "accent": "#EA580C",
            "neutral_bg": "#FFFBF5",
            "neutral_surface": "#FFFFFF",
            "ink": "#1C1917",
            "ink_soft": "#57534E",
        },
        "cool-modern": {
            "primary": "#0C0A09",
            "accent": "#06B6D4",
            "neutral_bg": "#FAFAF9",
            "neutral_surface": "#FFFFFF",
            "ink": "#0C0A09",
            "ink_soft": "#44403C",
        },
        "bold-vibrant": {
            "primary": "#000000",
            "accent": "#EAB308",
            "neutral_bg": "#FAFAFA",
            "neutral_surface": "#FFFFFF",
            "ink": "#000000",
            "ink_soft": "#404040",
        },
        "muted-elegant": {
            "primary": "#1E293B",
            "accent": "#94A3B8",
            "neutral_bg": "#F8FAFC",
            "neutral_surface": "#FFFFFF",
            "ink": "#0F172A",
            "ink_soft": "#475569",
        },
    },
}

PALETTE_HINTS: dict[str, list[str]] = {arch: list(p.keys()) for arch, p in PALETTES.items()}


def get_palette(archetype: str, hint: str) -> dict[str, str]:
    palettes = PALETTES[archetype]  # raises KeyError on unknown archetype
    if hint in palettes:
        return palettes[hint]
    return palettes[PALETTE_HINTS[archetype][0]]
