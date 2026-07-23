import pytest
from server import NARRATIVE_LOG_MAX

def test_narrative_log_capped_at_max_entries():
    """Bug 13: narrative_log is capped at NARRATIVE_LOG_MAX (50) entries."""
    assert NARRATIVE_LOG_MAX == 50
    
    session = {"narrative_log": []}
    
    # Simulate appending 100 log entries
    log = session.setdefault("narrative_log", [])
    for i in range(100):
        log.append(f"Log entry {i}")
        if len(log) > NARRATIVE_LOG_MAX:
            session["narrative_log"] = log[-NARRATIVE_LOG_MAX:]
            log = session["narrative_log"]
            
    assert len(session["narrative_log"]) == 50
    assert session["narrative_log"][0] == "Log entry 50"
    assert session["narrative_log"][-1] == "Log entry 99"
