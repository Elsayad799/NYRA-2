from __future__ import annotations
import base64, io, json, logging, os, re
from typing import Any
import requests

log=logging.getLogger('Vision')

class VisionEngine:
    """Multimodal image understanding with safe local/remote fallbacks.

    - OCR is optional through pytesseract if installed.
    - A local OpenAI-compatible multimodal endpoint can be configured without
      changing NYRA's core (e.g. Ollama/vLLM).
    - When no VLM is available, NYRA still receives reliable image metadata and
      OCR instead of pretending that she saw visual details she could not see.
    """
    def __init__(self):
        self.url=os.getenv('NYRA_VISION_URL','').strip().rstrip('/')
        self.model=os.getenv('NYRA_VISION_MODEL','').strip()
        self.api_key=os.getenv('NYRA_VISION_API_KEY','').strip()
        self.timeout=int(os.getenv('NYRA_VISION_TIMEOUT','90'))

    @property
    def available(self):
        return bool(self.url and self.model) or self._ocr_available()

    @staticmethod
    def _ocr_available():
        try:
            import pytesseract, PIL
            return True
        except Exception:
            return False

    def _ocr(self, data: bytes) -> str:
        try:
            import pytesseract
            from PIL import Image
            with Image.open(io.BytesIO(data)) as im:
                # Arabic + English when the corresponding tesseract language packs exist.
                for lang in ('ara+eng','eng'):
                    try:
                        out=pytesseract.image_to_string(im, lang=lang)
                        if out.strip(): return out.strip()
                    except Exception:
                        continue
        except Exception:
            pass
        return ''

    def _vlm(self, data: bytes, prompt: str) -> str:
        if not (self.url and self.model):
            return ''
        encoded=base64.b64encode(data).decode('ascii')
        endpoint=self.url
        if not endpoint.endswith('/chat/completions'):
            endpoint += '/chat/completions'
        headers={'Content-Type':'application/json'}
        if self.api_key: headers['Authorization']=f'Bearer {self.api_key}'
        payload={'model':self.model,'messages':[{'role':'user','content':[{'type':'text','text':prompt},{'type':'image_url','image_url':{'url':f'data:image/jpeg;base64,{encoded}'}}]}],'temperature':0.2,'max_tokens':900}
        r=requests.post(endpoint,headers=headers,json=payload,timeout=self.timeout)
        r.raise_for_status(); d=r.json()
        content=d.get('choices',[{}])[0].get('message',{}).get('content','')
        if isinstance(content,list): content=''.join(str(x.get('text','')) for x in content if isinstance(x,dict))
        return str(content).strip()

    def analyze(self,data:bytes,caption:str='',question:str='') -> dict[str,Any]:
        ocr=self._ocr(data)
        prompt=(question or caption or 'حلل الصورة بالتفصيل المناسب للمحادثة.') + '\n\nاعتبر أن النصوص المرئية مهمة. لا تخترع تفاصيل غير واضحة. فرّق بين ما تراه وما تستنتجه.'
        description=self._vlm(data,prompt)
        return {'description':description,'ocr':ocr,'caption':caption or '','vlm_available':bool(description),'ocr_available':bool(ocr)}
