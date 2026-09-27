from __future__ import annotations
import json, random, time, requests
from src.providers.base import AIResult

class MultiSearchProvider:
    """Adapter for the supplied ai.py multi-provider search backend."""
    name = "multi_search"
    model = "multi-provider"
    def __init__(self, firebase_key: str, search_url: str, providers: list[str]):
        self.firebase_key = firebase_key
        self.search_url = search_url
        self.providers = providers
        self._token = None
        self._expiry = 0.0
    def _get_token(self):
        if self._token and time.time() < self._expiry - 60:
            return self._token
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 16)",
            "Content-Type": "application/json",
            "X-Android-Package": "com.lmtechstudio.aimultisearch",
        }
        r = requests.post(
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser",
            params={"key": self.firebase_key}, json={"clientType":"CLIENT_TYPE_ANDROID"},
            headers=headers, timeout=30,
        )
        r.raise_for_status(); d = r.json()
        self._token = "Bearer " + d["idToken"]
        self._expiry = time.time() + int(d.get("expiresIn", 3600))
        return self._token
    def generate(self, messages, system=None, max_tokens=900):
        question = messages[-1]["content"] if messages else ""
        prompt = (system or "") + "\n\n" + question
        token = self._get_token()
        last = None; started = time.perf_counter()
        for provider in self.providers:
            cfg = {
                "perplexity": ("1.2.8", "825a35c5-aac2-49d7-8317-5b7a68ae6cae"),
                "claude": ("1.2.8", "825a35c5-aac2-49d7-8317-5b7a68ae6cae"),
                "openai": ("DEV_TEST", "f0a6705c-e33e-4288-a3ef-c91cd6564b59"),
                "deepseek": ("1.2.8", "f0a6705c-e33e-4288-a3ef-c91cd6564b59"),
                "gemini": ("1.2.8", "b2ed082e-5793-4de0-9e42-c8c7fb57b5d5"),
                "llama": ("1.2.8", "b2ed082e-5793-4de0-9e42-c8c7fb57b5d5"),
            }[provider]
            try:
                r = requests.post(self.search_url, json={"provider":provider,"prompt":prompt,"plan":"ULTRA","app_version":cfg[0]}, headers={"authorization":token,"x-plan":"ULTRA","x-app-version":cfg[0],"x-search-id":cfg[1],"x-search-expected":"2","content-type":"application/json"}, timeout=90)
                r.raise_for_status(); d=r.json()
                if d.get("ok") and d.get("answer"):
                    return AIResult(str(d["answer"]), f"multi_search:{provider}", provider, int((time.perf_counter()-started)*1000))
                last = RuntimeError(d.get("message", "empty answer"))
            except Exception as e:
                last = e
        raise RuntimeError(f"multi_search failed: {last}")

class AISeekProvider:
    """Adapter for the supplied ai_2.py SSE service."""
    name = "ai_seek"
    def __init__(self, access_token: str, model: str):
        self.access_token, self.model = access_token, model
    def generate(self, messages, system=None, max_tokens=900):
        text = (system or "") + "\n\n" + "\n".join(m["content"] for m in messages)
        started=time.perf_counter(); answer=""
        mid=f"{random.getrandbits(128):032x}"
        url="https://ai-seek.thebetter.ai/v4/chat/send"
        headers={"User-Agent":"okhttp/4.12.0","Accept":"text/event-stream","Content-Type":"application/json","x-app-id":"ai-seek","x-access-token":self.access_token}
        payload={"sessionId":f"nyra-{int(time.time())}","userMessageId":mid,"aiMessageId":f"{mid[:8]}-{mid[8:12]}-{mid[12:16]}-{mid[16:20]}-{mid[20:]}","model":self.model,"text":text,"restrictedType":"FREE_USER","sessionType":"NORMAL"}
        r=requests.post(url,json=payload,headers=headers,stream=True,timeout=120); r.raise_for_status()
        for line in r.iter_lines():
            if not line: continue
            raw=line.decode("utf-8",errors="ignore")
            if raw.startswith("data: "):
                try:
                    d=json.loads(raw[6:])
                    if d.get("content"): answer += str(d["content"])
                except json.JSONDecodeError: pass
        if not answer.strip(): raise RuntimeError("ai_seek returned empty response")
        return AIResult(answer.strip(),self.name,self.model,int((time.perf_counter()-started)*1000))

class LegacyQueryProvider:
    """Adapter for supplied simple ?q=... JSON endpoints."""
    name="legacy_query"
    model="legacy"
    def __init__(self,url): self.url=url
    def generate(self,messages,system=None,max_tokens=900):
        q=(system or "")+"\n\n"+messages[-1]["content"]
        started=time.perf_counter(); r=requests.get(self.url,params={"q":q},timeout=60); r.raise_for_status(); d=r.json()
        answer=d.get("answer") or d.get("response") or d.get("content")
        if not answer: raise RuntimeError("legacy endpoint returned no answer")
        return AIResult(str(answer),self.name,self.model,int((time.perf_counter()-started)*1000))
