from src.database.db import Database
from src.agent.goals import GoalStore
from src.agent.outcomes import OutcomeLearner

def test_goal_progress(tmp_path):
    db=Database(str(tmp_path/'g.db')); g=GoalStore(db)
    row=g.add('group',-100,'تعلم موضوع Minecraft',.8)
    assert row['id']
    assert float(g.open('group',-100,1)[0]['progress'])==0
    assert g.progress(row['id'],.25,'first successful action') == .25

def test_goal_completion(tmp_path):
    db=Database(str(tmp_path/'g.db')); g=GoalStore(db)
    row=g.add('group',-100,'هدف',.5)
    assert g.progress(row['id'],1.0,'completed') == 1.0
    assert not g.open('group',-100,5)

def test_outcome_updates_goal(tmp_path):
    db=Database(str(tmp_path/'g.db')); g=GoalStore(db); o=OutcomeLearner(db)
    row=g.add('group',-100,'شارك في موضوع',.8)
    aid=o.record_action(-100,'proactive_message','goal_alignment','topic',0,'hello',row['id'])
    result=o.resolve(aid,'response',.75,'human replied')
    assert result['goal_id']==row['id']
    assert float(g.open('group',-100,1)[0]['progress']) > 0
