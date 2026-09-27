"""NYRA image style catalog. Style names are prompt modifiers, not provider credentials."""
STYLES = {
    "natural": "natural photorealistic photography",
    "street": "street photography, realistic urban scene",
    "architecture": "architectural photography, clean geometry",
    "food": "editorial food photography",
    "fashion": "high-end fashion editorial photography",
    "automotive": "automotive photography, dramatic composition",
    "sports": "dynamic sports photography",
    "wildlife": "wildlife photography, natural detail",
    "macro_insect": "extreme macro photography",
    "astro": "astrophotography, detailed night sky",
    "aerial": "aerial photography, cinematic composition",
    "oil_painting": "classical oil painting texture",
    "watercolor": "detailed watercolor illustration",
    "surrealist": "surrealist dreamlike visual composition",
    "cyberpunk": "cinematic cyberpunk neon aesthetic",
}

def apply_style(prompt: str, style: str | None) -> str:
    prompt=(prompt or "").strip()
    modifier=STYLES.get((style or "").strip().lower())
    return f"{prompt}, {modifier}" if modifier else prompt
