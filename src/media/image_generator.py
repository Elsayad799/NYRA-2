from __future__ import annotations
import logging, os
from .image_providers import PollinationsProvider, HuggingFaceProvider, ComfyUIProvider, OpenAICompatibleProvider

log=logging.getLogger('ImageGenerator')

class ImageGenerator:
    """Multi-provider image failover. Tries every configured/usable backend in order."""
    def __init__(self):
        self.providers=[PollinationsProvider(), HuggingFaceProvider(), ComfyUIProvider(), OpenAICompatibleProvider()]
        requested=[x.strip().lower() for x in os.getenv('IMAGE_PROVIDER_ORDER','pollinations,huggingface,comfyui,openai_compatible_image').split(',') if x.strip()]
        rank={name:i for i,name in enumerate(requested)}
        self.providers.sort(key=lambda p: rank.get(p.name,999))
        self.last_provider=None
        self.last_errors=[]
    @property
    def available(self):
        return any(p.available() for p in self.providers)
    @property
    def status(self):
        parts=[]
        for p in self.providers:
            try: state='READY' if p.available() else 'OFF'
            except Exception: state='OFF'
            parts.append(f'{p.name}={state}')
        return ' | '.join(parts)
    def generate(self,prompt,aspect_ratio='1:1',count=1):
        prompt=(prompt or '').strip()
        if not prompt: raise ValueError('image prompt is empty')
        self.last_errors=[]
        for provider in self.providers:
            try:
                if not provider.available():
                    continue
                result=provider.generate(prompt,aspect_ratio,max(1,min(int(count),4)))
                if result and result.images:
                    self.last_provider=result.provider
                    return result.images
            except Exception as exc:
                msg=f'{provider.name}: {type(exc).__name__}: {exc}'
                self.last_errors.append(msg); log.exception('image provider failed: %s',provider.name)
                continue
        detail='; '.join(self.last_errors[-5:]) or 'no configured image provider is ready'
        raise RuntimeError(f'all image providers failed; no images generated: {detail}')
