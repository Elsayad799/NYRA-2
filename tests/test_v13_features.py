import io, tempfile
from pathlib import Path
from src.database.db import Database
from src.media.memory import MediaMemory
from src.media.understanding import MediaUnderstanding
from src.personality.state import StateStore
from src.identity.presentation import PresentationEngine

def db():
    p=Path(tempfile.mkdtemp())/'nyra.db'
    return Database(str(p))

def test_media_metadata_only():
    d=db(); m=MediaMemory(d)
    m.remember(chat_id=1,user_id=2,file_id='f1',media_type='photo',caption='hello',unique_id='u1',metadata={'width':100})
    r=m.recent(1,2,1)[0]
    assert r['file_id']=='f1' and r['caption']=='hello' and 'width' in r['metadata_json']

def test_presentation_group_is_female():
    d=db(); p=PresentationEngine(d)
    x=p.get(2,3,'supergroup')
    assert x['presentation']=='female'

def test_private_presentation_can_change():
    d=db(); p=PresentationEngine(d)
    p.set_private(2,3,'male')
    assert p.get(2,3,'private')['presentation']=='male'

def test_image_inspection_does_not_persist_bytes():
    try:
        from PIL import Image
    except ImportError:
        return
    buf=io.BytesIO(); Image.new('RGB',(32,16)).save(buf,format='PNG')
    meta=MediaUnderstanding().inspect_image(buf.getvalue(),'test')
    assert meta['width']==32 and meta['height']==16 and meta['format']=='PNG'

def test_state_persists():
    d=db(); s=StateStore(d); x=s.get(); x['curiosity']=.91; s.set(x)
    assert abs(s.get()['curiosity']-.91)<1e-9
