from src.database.db import Database
from src.agent.outcomes import OutcomeLearner

def test_outcome_learning_from_response(tmp_path):
    db=Database(str(tmp_path/'o.db')); o=OutcomeLearner(db)
    aid=o.record_action(1,'proactive_message','active_topic','Minecraft',0,'تعالوا نتكلم عن Minecraft')
    r=o.observe_message(1,22,'ايوه يلا')
    assert r and r['outcome']=='response' and r['reward']>0
    assert o.bias('proactive_message','active_topic')>0

def test_no_reward_without_observation(tmp_path):
    db=Database(str(tmp_path/'o.db')); o=OutcomeLearner(db)
    o.record_action(1,'proactive_message','active_topic','Minecraft',0,'hello')
    assert o.bias('proactive_message','active_topic') == 0
