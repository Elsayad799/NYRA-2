from __future__ import annotations
import time, requests
from src.providers.base import AIResult

class GeminiProvider:
    name="gemini"
    def __init__(self,key,model): self.key,self.model=key,model
    def generate(self,messages,system=None,max_tokens=900):
        if not self.key: raise RuntimeError("GEMINI_API_KEY missing")
        contents=[]
        if system: contents.append({"role":"user","parts":[{"text":"SYSTEM INSTRUCTIONS:\n"+system}]})
        for m in messages: contents.append({"role":"model" if m["role"]=="assistant" else "user","parts":[{"text":m["content"]}]})
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        t=time.perf_counter(); r=requests.post(url,params={"key":self.key},json={"contents":contents,"generationConfig":{"maxOutputTokens":max_tokens}},timeout=90); r.raise_for_status(); d=r.json()
        text=d["candidates"][0]["content"]["parts"][0]["text"]
        return AIResult(text,self.name,self.model,int((time.perf_counter()-t)*1000))
