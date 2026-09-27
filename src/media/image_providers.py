from __future__ import annotations
import base64, io, json, os, time, urllib.parse, uuid
from dataclasses import dataclass
from typing import Any
import requests

@dataclass
class ProviderResult:
    provider: str
    images: list[Any]

class BaseImageProvider:
    name = 'base'
    def available(self) -> bool: return False
    def generate(self, prompt: str, aspect_ratio: str='1:1', count: int=1) -> ProviderResult:
        raise NotImplementedError

class PollinationsProvider(BaseImageProvider):
    name = 'pollinations'
    def __init__(self):
        self.base = os.getenv('POLLINATIONS_BASE_URL', 'https://gen.pollinations.ai').rstrip('/')
        self.key = os.getenv('POLLINATIONS_API_KEY', '').strip()
    def available(self): return True
    def generate(self, prompt, aspect_ratio='1:1', count=1):
        sizes = {'1:1':(1024,1024),'16:9':(1280,720),'9:16':(720,1280),'4:3':(1152,864),'3:4':(864,1152)}
        w,h=sizes.get(aspect_ratio,(1024,1024)); out=[]
        headers={'Authorization':f'Bearer {self.key}'} if self.key else {}
        # Official gateway currently documents API-key auth. Try it when configured.
        if self.key:
            for _ in range(max(1,min(count,4))):
                u=f"{self.base}/image/{urllib.parse.quote(prompt, safe='')}"
                r=requests.get(u, params={'model':os.getenv('POLLINATIONS_MODEL','zimage'),'width':w,'height':h}, headers=headers, timeout=120)
                r.raise_for_status(); out.append(r.content)
            return ProviderResult(self.name,out)
        # Compatibility fallback for deployments that still expose the legacy public endpoint.
        legacy=os.getenv('POLLINATIONS_LEGACY_URL','https://image.pollinations.ai/prompt').rstrip('/')
        for _ in range(max(1,min(count,4))):
            u=f"{legacy}/{urllib.parse.quote(prompt, safe='')}"
            r=requests.get(u, params={'model':os.getenv('POLLINATIONS_MODEL','flux'),'width':w,'height':h,'nologo':'true'}, timeout=120)
            r.raise_for_status(); out.append(r.content)
        return ProviderResult(self.name,out)

class HuggingFaceProvider(BaseImageProvider):
    name = 'huggingface'
    def __init__(self):
        self.token=os.getenv('HF_TOKEN','').strip()
        self.model=os.getenv('HF_IMAGE_MODEL','black-forest-labs/FLUX.1-dev').strip()
    def available(self): return bool(self.token)
    def generate(self,prompt,aspect_ratio='1:1',count=1):
        if not self.token: raise RuntimeError('HF_TOKEN not configured')
        from huggingface_hub import InferenceClient
        client=InferenceClient(api_key=self.token)
        out=[]
        for _ in range(max(1,min(count,4))):
            img=client.text_to_image(prompt=prompt, model=self.model)
            buf=io.BytesIO(); img.save(buf,format='PNG'); out.append(buf.getvalue())
        return ProviderResult(self.name,out)

class ComfyUIProvider(BaseImageProvider):
    name = 'comfyui'
    def __init__(self):
        self.base=os.getenv('COMFYUI_BASE_URL','http://127.0.0.1:8188').rstrip('/')
        self.workflow_path=os.getenv('COMFYUI_WORKFLOW','').strip()
    def available(self):
        try:
            r=requests.get(f'{self.base}/system_stats',timeout=3)
            return r.ok
        except Exception: return False
    def generate(self,prompt,aspect_ratio='1:1',count=1):
        if not self.workflow_path or not os.path.exists(self.workflow_path):
            raise RuntimeError('COMFYUI_WORKFLOW is not configured')
        # API-format workflow exported from ComfyUI. Replace the first CLIP positive text and random seed.
        with open(self.workflow_path,'r',encoding='utf-8') as f: wf=json.load(f)
        found=False
        for node in wf.values():
            if isinstance(node,dict) and node.get('class_type')=='CLIPTextEncode':
                text=node.get('inputs',{}).get('text','')
                if not found and isinstance(text,str):
                    node['inputs']['text']=prompt; found=True
        if not found: raise RuntimeError('workflow has no CLIPTextEncode positive node')
        # Queue one request per image and retrieve the first output image.
        client_id=str(uuid.uuid4())
        r=requests.post(f'{self.base}/prompt',json={'prompt':wf,'client_id':client_id},timeout=20); r.raise_for_status()
        pid=r.json().get('prompt_id')
        if not pid: raise RuntimeError('ComfyUI returned no prompt_id')
        deadline=time.time()+300
        while time.time()<deadline:
            h=requests.get(f'{self.base}/history/{pid}',timeout=20); h.raise_for_status(); data=h.json().get(pid)
            if data and data.get('outputs'):
                for output in data['outputs'].values():
                    for img in output.get('images',[]):
                        params={'filename':img['filename'],'subfolder':img.get('subfolder',''),'type':img.get('type','output')}
                        rr=requests.get(f'{self.base}/view',params=params,timeout=60); rr.raise_for_status(); return ProviderResult(self.name,[rr.content])
            time.sleep(1)
        raise RuntimeError('ComfyUI generation timed out')

class OpenAICompatibleProvider(BaseImageProvider):
    name='openai_compatible_image'
    def __init__(self):
        self.url=os.getenv('IMAGE_API_URL','').strip()
        self.key=os.getenv('IMAGE_API_KEY','').strip()
        self.model=os.getenv('IMAGE_API_MODEL','black-forest-labs/FLUX.1-schnell').strip()
    def available(self): return bool(self.url and self.key)
    def generate(self,prompt,aspect_ratio='1:1',count=1):
        if not self.available(): raise RuntimeError('IMAGE_API_URL/IMAGE_API_KEY not configured')
        r=requests.post(self.url,headers={'Authorization':f'Bearer {self.key}'},json={'model':self.model,'prompt':prompt,'n':1,'size':'1024x1024'},timeout=180); r.raise_for_status()
        data=r.json(); out=[]
        for item in data.get('data',[]):
            if item.get('b64_json'): out.append(base64.b64decode(item['b64_json']))
            elif item.get('url'): out.append(item['url'])
        if not out: raise RuntimeError('compatible image API returned no image')
        return ProviderResult(self.name,out)
