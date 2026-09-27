from src.media.youtube import YouTubeAudio
from src.media.visual_identity import DEFAULT_VISUAL_DNA


def test_nyra_visual_dna_is_photorealistic_and_blocks_cartoon_styles():
    low=DEFAULT_VISUAL_DNA.lower()
    assert 'photorealistic' in low
    assert 'real-life human photography' in low
    assert 'natural skin pores' in low
    for forbidden in ('anime', 'cartoon', 'illustration', '3d render', 'cgi', 'doll'):
        assert forbidden in low


def test_music_contextual_followup_code_is_present():
    from pathlib import Path
    text=Path('src/telegram/adapter.py').read_text(encoding='utf-8')
    assert '_pending_music' in text
    assert '_music_followup' in text
