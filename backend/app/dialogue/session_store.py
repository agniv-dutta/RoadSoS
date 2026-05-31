from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Dict, Optional


@dataclass
class SessionState:
    id: str
    state: str = "INITIAL"
    filled_slots: Dict[str, any] = field(default_factory=dict)
    turn_count: int = 0
    ask_counts: Dict[str, int] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: time.time())
    last_active: float = field(default_factory=lambda: time.time())
    # holds a per-session transitions Machine instance (optional)
    machine: any = None


class SessionStore:
    def __init__(self, expiry_seconds: int = 300):
        self._store: Dict[str, SessionState] = {}
        self.expiry_seconds = expiry_seconds

    def get(self, session_id: str) -> Optional[SessionState]:
        s = self._store.get(session_id)
        if s is None:
            return None
        # check expiry
        if time.time() - s.last_active > self.expiry_seconds:
            # expire
            del self._store[session_id]
            return None
        return s

    def create(self, session_id: str) -> SessionState:
        s = SessionState(id=session_id)
        self._store[session_id] = s
        return s

    def update(self, session_id: str, **kwargs):
        s = self._store.get(session_id)
        if not s:
            return None
        for k, v in kwargs.items():
            if hasattr(s, k):
                setattr(s, k, v)
        s.last_active = time.time()
        return s

    def cleanup_expired(self):
        now = time.time()
        expired = [sid for sid, s in self._store.items() if now - s.last_active > self.expiry_seconds]
        for sid in expired:
            del self._store[sid]

    def all_sessions(self):
        return list(self._store.values())

    def clear(self):
        self._store.clear()
