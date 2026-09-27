import time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from src.database.db import Database
from src.social.brain import SocialBrain
from src.core.config import Settings
from src.personality.state import StateStore
from src.media.visual_identity import VisualIdentityStore


def settings():
    return Settings(
        telegram_token='test', admin_ids=frozenset(), database_url=':memory:', debug=False,
        autonomous_mode=True, global_cooldown=0, group_cooldown=0, user_cooldown=0,
        autonomous_budget_per_hour=6, autonomous_interval=15, max_history=16, max_memories=12,
        primary_provider='supplied', openai_api_key=None, openai_base_url='', openai_model='',
        groq_api_key=None, groq_model='', gemini_api_key=None, gemini_model='',
        anthropic_api_key=None, anthropic_model='', legacy_ai_url=None, image_url=None,
        multi_search_key=None, multi_search_url='', ai_seek_token=None, ai_seek_model='', legacy_query_url=None
    )


def test_private_candidate_can_be_selected_after_silence():
    db=Database(':memory:')
    db.execute("INSERT INTO users(user_id,name,username,first_seen,last_seen,interaction_count) VALUES(1,'A','a',datetime('now'),datetime('now','-2 days'),4)")
    db.execute("INSERT INTO relationships(user_id,chat_id,trust,familiarity,interaction_count) VALUES(1,1,.8,.8,4)")
    brain=SocialBrain(db,settings())
    state=StateStore(db).get()
    state.update({'social_need':.9,'desire_to_talk':.9,'attachment':.8,'energy':.8})
    d=brain.private_proactive_decision(dict(db.query('SELECT u.*,r.trust,r.familiarity FROM users u JOIN relationships r ON r.user_id=u.user_id AND r.chat_id=u.user_id')[0]),state)
    assert d['action']=='contact'


def test_visual_dna_is_shared_and_persistent():
    db=Database(':memory:')
    v=VisualIdentityStore(db,None)
    a=v.ensure(); b=v.ensure()
    assert a==b
    assert 'NYRA' in a
    p=v.build_prompt(1,1,{'mood':'curious'},request='hoodie',scene='night')
    assert a in p and 'hoodie' in p and 'night' in p
