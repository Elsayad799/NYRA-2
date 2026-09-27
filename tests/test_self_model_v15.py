from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.database.db import Database
from src.agent.self_model import SelfModel
from src.social.conversation import SocialConversationEngine
from src.media.visual_identity import VisualIdentityStore

def test_self_model_persists():
    db=Database(":memory:")
    sm=SelfModel(db)
    sm.update(desires=["understand people", "explore"])
    assert sm.get()["identity_name"]=="NYRA AI"
    assert "explore" in sm.get()["desires"]

def test_social_modes_avoid_helpdesk_mode():
    db=Database(":memory:")
    sm=SelfModel(db)
    ce=SocialConversationEngine()
    assert ce.classify("عايزك تبقي جنبي", sm.get())=="COMPANIONSHIP"
    assert ce.classify("الحب", sm.get())=="EMOTIONAL"
    assert "customer-service" not in ce.prompt_fragment("COMPANIONSHIP")

def test_visual_files_are_written(tmp_path):
    db=Database(str(tmp_path/"nyra.db"))
    v=VisualIdentityStore(db,None)
    base=v.ensure()
    p=v.build_prompt(123,123,{"mood":"curious"},scene="night")
    assert base in p
    assert (tmp_path/"nyra_visual"/"nyra_visual_dna.json").exists()
    assert (tmp_path/"nyra_visual"/"user_123.json").exists()

def test_self_model_tracks_capabilities_environment_and_lessons():
    db=Database(":memory:")
    sm=SelfModel(db)
    sm.record_capability("music", evidence="youtube tool initialized", confidence=.8)
    sm.observe_environment(chat_type="private", media_type="voice", tools=["play_music"])
    sm.learn_from_outcome("music request succeeded", evidence="audio sent", confidence=.9)
    m=sm.get()
    assert m["capabilities"]["music"]["available"] is True
    assert "private" in m["environment"]["chat_types"]
    assert "voice" in m["environment"]["media_types"]
    assert "play_music" in m["environment"]["known_tools"]
    assert "music request succeeded" in m["recent_lessons"]
