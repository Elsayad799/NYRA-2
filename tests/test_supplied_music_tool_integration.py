from pathlib import Path


def test_supplied_music_tool_is_kept_intact():
    root = Path('integrations/youtube_music_download_bot')
    assert (root / 'src' / 'bot.py').exists()
    assert (root / 'src' / 'tgbot' / 'services' / 'youtube.py').exists()
    assert (root / 'src' / 'requirements.txt').exists()


def test_bridge_loads_original_tool_without_starting_second_bot():
    text = Path('integrations/tg_music_bot/bridge.py').read_text(encoding='utf-8')
    assert 'youtube as original_youtube' in text
    assert 'start_bot' not in text
    assert 'download_original_sync' in text


def test_groups_route_music_to_voice_chat():
    text = Path('src/telegram/adapter.py').read_text(encoding='utf-8')
    assert "{'group', 'supergroup'}" in text
    assert 'self._play_voice_chat(message, query)' in text


def test_private_chat_routes_original_downloader_first():
    text = Path('src/telegram/adapter.py').read_text(encoding='utf-8')
    assert 'self.tg_music.original_search(query, \'en\')' in text
    assert 'self.tg_music.download_original_sync(row[\'url\'])' in text
