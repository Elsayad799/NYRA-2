import json
from src.providers.source_ai import MultiSearchProvider, AISeekProvider

class Resp:
    def __init__(self,data=None,lines=None): self.data=data; self._lines=lines or []
    def raise_for_status(self): pass
    def json(self): return self.data
    def iter_lines(self): return self._lines

def test_multisearch_adapter(monkeypatch):
    calls=[]
    def post(url, **kw):
        calls.append(url)
        if "identitytoolkit" in url: return Resp({"idToken":"x","expiresIn":"3600"})
        return Resp({"ok":True,"answer":"hello"})
    monkeypatch.setattr("src.providers.source_ai.requests.post",post)
    r=MultiSearchProvider("k","https://search/ask",["gemini"]).generate([{"role":"user","content":"hi"}])
    assert r.text=="hello" and r.provider=="multi_search:gemini" and len(calls)==2

def test_ai_seek_sse(monkeypatch):
    lines=[b'data: {"content":"hello "}',b'data: {"content":"NYRA"}']
    monkeypatch.setattr("src.providers.source_ai.requests.post",lambda *a,**k: Resp(lines=lines))
    r=AISeekProvider("token","model").generate([{"role":"user","content":"hi"}])
    assert r.text=="hello NYRA" and r.provider=="ai_seek"
