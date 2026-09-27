from src.database.db import Database
from src.social.attention import AttentionManager
from src.social.relationship import RelationshipEngine
from src.social.brain import SocialBrain
from src.agent.events import Event
from types import SimpleNamespace

def test_direct_attention_is_high(tmp_path):
    db=Database(str(tmp_path/'a.db')); a=AttentionManager(db); r=RelationshipEngine(db); s=SocialBrain(db,SimpleNamespace(global_cooldown=0,group_cooldown=0,user_cooldown=0),a,r)
    e=Event(chat_id=1,user_id=2,message_id=3,text='NYRA ايه رأيك؟',chat_type='group',is_mention=True)
    a.observe(e); r.observe(e); d=s.choose(e,r.get(2,1),{'mood':'curious','energy':.8,'social_need':.5,'curiosity':.8,'happiness':.6,'sadness':0,'anger':0})
    assert d['action']=='reply' and d['attention']>=0
