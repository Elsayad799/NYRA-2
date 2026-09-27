import tempfile
from types import SimpleNamespace
from src.database.db import Database
from src.memory.store import MemoryStore
from src.memory.active_recall import ActiveRecall
from src.social.attention import AttentionManager
from src.social.brain import SocialBrain

class S:
    global_cooldown=0; group_cooldown=0; user_cooldown=0

def event(text, mid=1, uid=10, chat=20):
    return SimpleNamespace(chat_id=chat,user_id=uid,message_id=mid,chat_type='supergroup',text=text,user_name='U',username='u',chat_title='G',is_reply_to_bot=False,is_mention=False)

def test_active_recall():
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        db=Database(f.name); mem=MemoryStore(db)
        mem.upsert('group',20,'topic','Ahmed and NYRA discussed Minecraft builds yesterday',.8,.9,'observed')
        r=ActiveRecall(db,mem).find(20,10,'Minecraft builds',4)
        assert r and r[0]['content'].startswith('Ahmed and NYRA')

def test_attention_and_social_decision():
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        db=Database(f.name); att=AttentionManager(db)
        brain=SocialBrain(db,S(),att,None)
        e=event('What do you think about this?',2)
        att.observe(e)
        result=brain.choose(e,{'familiarity':.5},{'mood':'curious','energy':.8,'social_need':.5,'curiosity':.9,'happiness':.7,'sadness':.1,'anger':.05})
        assert result['action'] in {'reply','ignore'}
        assert 0 <= result['score'] <= 1

def test_no_fake_recall():
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        db=Database(f.name); mem=MemoryStore(db)
        mem.upsert('group',20,'topic','We talked about cooking pasta',.5,.8,'observed')
        assert ActiveRecall(db,mem).find(20,10,'quantum mechanics',4) == []
