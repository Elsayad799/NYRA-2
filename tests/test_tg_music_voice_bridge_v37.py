from pathlib import Path
import zipfile


def test_tg_music_original_tree_is_present():
    root = Path('integrations/tg_music_voice_full/TgMusicBot-master')
    assert (root / 'main.go').exists()
    assert (root / 'internal/calls/call.go').exists()
    assert (root / 'internal/calls/playback.go').exists()
    assert (root / 'internal/config/save_cookies.go').exists()


def test_nyra_bridge_is_additive():
    p = Path('integrations/tg_music_voice_full/TgMusicBot-master/cmd/nyra_voice_bridge/main.go')
    text = p.read_text(encoding='utf-8')
    assert 'calls.Calls.PlayMedia' in text
    assert 'calls.Calls.Pause' in text
    assert 'calls.Calls.Resume' in text
    assert 'calls.Calls.Stop' in text


def test_adapter_prefers_tg_music_sidecar():
    text = Path('src/telegram/adapter.py').read_text(encoding='utf-8')
    assert 'TgMusicVoiceBridge' in text
    assert 'self.tg_voice_bridge.play' in text
    assert 'video=video' in text


def test_original_cookie_support_not_removed():
    text = Path('integrations/tg_music_voice_full/TgMusicBot-master/internal/config/load.go').read_text(encoding='utf-8')
    assert 'COOKIES_URL' in text or 'cookiesUrl' in text
    assert 'saveAllCookies' in text
