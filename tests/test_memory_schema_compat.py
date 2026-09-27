import tempfile
from pathlib import Path
from src.database.db import Database

def test_recent_nyra_memory_query_uses_actual_schema():
    db = Database(str(Path(tempfile.mkdtemp()) / "nyra.db"))
    db.execute(
        "INSERT INTO memories(scope,owner_id,kind,content,importance,confidence,source,created_at,last_used) "
        "VALUES(?,?,?,?,?,?,?,datetime(\'now\'),datetime(\'now\'))",
        ("episodic", "123", "nyra_response", "hello", .3, .65, "agent_response"),
    )
    rows = db.query(
        "SELECT content FROM memories WHERE scope=\'episodic\' AND owner_id=? "
        "AND kind=\'nyra_response\' AND source=\'agent_response\' ORDER BY id DESC LIMIT 6",
        ("123",),
    )
    assert rows and rows[0]["content"] == "hello"
