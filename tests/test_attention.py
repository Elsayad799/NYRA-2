from src.database.db import Database
from src.social.attention import AttentionManager
from src.social.relationship import RelationshipEngine
from src.agent.events import Event

def test_attention_tracks_topic_and_user(tmp_path):
    db=Database(str(tmp_path/'a.db')); a=AttentionManager(db); r=RelationshipEngine(db)
    e=Event(chat_id=10,user_id=22,message_id=1,text='مين جرب ماينكرافت؟',chat_type='group',chat_title='G',user_name='A',username='a')
    a.observe(e); r.observe(e)
    x=a.get(10)
    assert x['target_user_id']==22 and x['topic'] and x['turns_since_reply']==1

def test_attention_resets_after_reply(tmp_path):
    db=Database(str(tmp_path/'a.db')); a=AttentionManager(db)
    e=Event(chat_id=10,user_id=22,message_id=1,text='hello world',chat_type='group')
    a.observe(e); a.mark_attention(10,22)
    assert a.get(10)['turns_since_reply']==0
