import json
from src.database.db import Database
from src.agent.planner import PlanStore, PlanningEngine, ALLOWED_ACTIONS

class FakeProvider:
    def generate(self, messages, system=None, max_tokens=500):
        class R: pass
        r=R(); r.text=json.dumps({"title":"تعلم الموضوع","steps":[
            {"action_type":"observe","objective":"راقب الرسائل الحالية"},
            {"action_type":"send_message","objective":"شارك سؤالًا قصيرًا مرتبطًا بالموضوع"},
            {"action_type":"reflect","objective":"راجع نتيجة الخطوة السابقة"}
        ]}); return r

def test_plan_creation_and_step_execution(tmp_path):
    db=Database(str(tmp_path/'p.db')); store=PlanStore(db)
    plan=store.create(1,-100,'plan',[{"action_type":"observe","objective":"observe"},{"action_type":"send_message","objective":"ask"}])
    assert plan and store.next_step(plan['id'])['action_type']=='observe'
    step=store.next_step(plan['id']); store.complete_step(step['id'],'done')
    assert store.next_step(plan['id'])['action_type']=='send_message'

def test_planner_validates_actions(tmp_path):
    db=Database(str(tmp_path/'p.db')); store=PlanStore(db)
    plan=store.create(1,-100,'plan',[{"action_type":"shell","objective":"rm -rf /"},{"action_type":"send_message","objective":"say hi"}])
    assert plan and store.next_step(plan['id'])['action_type']=='send_message'

def test_planning_engine_builds_bounded_plan(tmp_path):
    db=Database(str(tmp_path/'p.db')); store=PlanStore(db)
    goal={'id':1,'goal':'تعلم موضوع Minecraft'}
    engine=PlanningEngine(db,FakeProvider(),store)
    plan=engine.ensure_plan(goal,-100,'Minecraft','hello')
    assert plan and 2 <= len(db.query('SELECT id FROM plan_steps WHERE plan_id=?',(plan['id'],))) <= 5
    assert all(r['action_type'] in ALLOWED_ACTIONS for r in db.query('SELECT * FROM plan_steps WHERE plan_id=?',(plan['id'],)))
