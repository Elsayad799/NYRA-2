from src.database.db import Database
from src.memory.store import MemoryStore

def test_memory_recall(tmp_path):
    db=Database(str(tmp_path/'t.db')); m=MemoryStore(db)
    m.upsert('user',1,'preference','يحب ماينكرافت',.8,.9)
    rows=m.recall('user',1,'ماينكرافت')
    assert rows and 'ماينكرافت' in rows[0]['content']
