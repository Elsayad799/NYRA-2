from src.database.db import Database
from src.social.conflict import ConflictEngine

def test_conflict_separates_anger_from_frustration(tmp_path):
    db=Database(str(tmp_path/'db.sqlite'))
    c=ConflictEngine(db)
    s=c.observe(1,100,'كل شوية بتعمل نفس الحاجة، بطل بقى')
    assert s['frustration'] > s['anger']
    assert s['forgiveness_status'] in ('pending','not_ready')

def test_apology_can_move_toward_forgiveness(tmp_path):
    db=Database(str(tmp_path/'db.sqlite'))
    c=ConflictEngine(db)
    for _ in range(2): c.observe(1,100,'اسكت بقى')
    before=c.get(1,100)
    c.observe(1,100,'آسف، حقك عليا')
    after=c.get(1,100)
    assert after['anger'] < before['anger']
    assert after['forgiveness'] > before['forgiveness']

def test_positive_behavior_can_reach_forgiven(tmp_path):
    db=Database(str(tmp_path/'db.sqlite'))
    c=ConflictEngine(db)
    c.observe(1,100,'غبي')
    c.observe(1,100,'آسف')
    c.observe(1,100,'شكرا، تمام')
    c.observe(1,100,'حاضر، شكرا')
    s=c.get(1,100)
    assert s['forgiveness_status'] == 'forgiven'
