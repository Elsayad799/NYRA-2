from src.tools.telegram_info import TelegramPublicInfo
from src.tools.link_inspector import LinkInspector

def test_public_info_sanitizes_sensitive_fields(monkeypatch):
    class R:
        def raise_for_status(self): pass
        def json(self): return {"user":{"username":"x","phone":"secret","accessHash":"secret2","firstName":"X","verified":True}}
    monkeypatch.setattr("requests.post", lambda *a, **k: R())
    out=TelegramPublicInfo.lookup("@x")
    assert out["username"]=="x" and "phone" not in out and "accessHash" not in out

def test_link_inspector_normalizes_url(monkeypatch):
    class R:
        url='https://example.com/'
        status_code=200
        headers={'content-type':'text/html','server':'test'}
    monkeypatch.setattr("requests.get", lambda *a, **k: R())
    out=LinkInspector.inspect("example.com")
    assert out["url"]=="https://example.com" and out["https"] is True
