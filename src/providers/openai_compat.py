from __future__ import annotations
import time, requests
from src.providers.base import AIResult

class OpenAICompatible:
    def __init__(self,name,api_key,base_url,model):
        self.name,self.api_key,self.base_url,self.model=name,api_key,base_url.rstrip('/'),model
    def generate(self,messages,system=None,max_tokens=900):
        if not self.api_key: raise RuntimeError(f"{self.name} API key missing")
        msgs=([{"role":"system","content":system}] if system else []) + messages
        t=time.perf_counter(); r=requests.post(self.base_url+"/chat/completions",headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"},json={"model":self.model,"messages":msgs,"max_tokens":max_tokens},timeout=90); r.raise_for_status(); d=r.json()
        text=d["choices"][0]["message"]["content"]
        return AIResult(text,self.name,self.model,int((time.perf_counter()-t)*1000))
