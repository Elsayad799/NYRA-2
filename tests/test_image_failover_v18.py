import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.media.image_generator import ImageGenerator
from src.media.image_providers import ProviderResult

def test_failover():
    g=ImageGenerator()
    class Bad:
        name='bad';
        def available(self): return True
        def generate(self,*a,**k): raise RuntimeError('boom')
    class Good:
        name='good';
        def available(self): return True
        def generate(self,*a,**k): return ProviderResult('good',[b'PNG'])
    g.providers=[Bad(),Good()]
    assert g.generate('test')==[b'PNG']
    assert g.last_provider=='good'

def test_status_mentions_backends():
    g=ImageGenerator()
    s=g.status
    assert 'pollinations=' in s and 'huggingface=' in s and 'comfyui=' in s
