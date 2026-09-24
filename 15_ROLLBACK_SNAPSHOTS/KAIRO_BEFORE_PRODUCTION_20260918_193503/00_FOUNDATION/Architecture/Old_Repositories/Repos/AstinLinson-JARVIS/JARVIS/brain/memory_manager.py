"""Memory abstractions and the long-term memory implementation."""

from __future__ import annotations

import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from JARVIS.brain.memory_tagger import MemoryTagger
from JARVIS.models.interfaces import MemoryStore
from JARVIS.models.types import Message


class ConversationMemoryStore(MemoryStore, ABC):
    """Conversation memory boundary for chat-style message history."""


class LongTermMemoryStore:
    """Manages Identity, Preferences, and Long-Term Events on disk."""
    
    def __init__(self, memory_dir: Path) -> None:
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.identity_file = self.memory_dir / "identity.json"
        self.preferences_file = self.memory_dir / "preferences.json"
        self.memories_file = self.memory_dir / "memories.jsonl"
        
        self._ensure_files()

    def _ensure_files(self) -> None:
        if not self.identity_file.exists():
            self.identity_file.write_text("{}", encoding="utf-8")
        if not self.preferences_file.exists():
            self.preferences_file.write_text("{}", encoding="utf-8")

    def save_identity(self, fact: str) -> str:
        data = json.loads(self.identity_file.read_text(encoding="utf-8"))
        # deduplication naive check
        for k, v in data.items():
            if v["content"].lower() == fact.lower():
                return k
        fact_id = str(uuid.uuid4())
        data[fact_id] = {"content": fact, "timestamp": time.time()}
        self.identity_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return fact_id

    def save_preference(self, pref: str) -> str:
        data = json.loads(self.preferences_file.read_text(encoding="utf-8"))
        for k, v in data.items():
            if v["content"].lower() == pref.lower():
                return k
        pref_id = str(uuid.uuid4())
        data[pref_id] = {"content": pref, "timestamp": time.time()}
        self.preferences_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return pref_id

    def save_event(self, event: str, importance: int = 1) -> str:
        # deduplication check
        events = self.get_events()
        for e in events:
            if e["content"].lower() == event.lower():
                return e["uuid"]
                
        record = {
            "uuid": str(uuid.uuid4()),
            "timestamp": time.time(),
            "category": "event",
            "importance": importance,
            "source": "user",
            "tags": [],
            "content": event
        }
        with self.memories_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record["uuid"]

    def get_identities(self) -> dict[str, Any]:
        return json.loads(self.identity_file.read_text(encoding="utf-8"))
        
    def get_preferences(self) -> dict[str, Any]:
        return json.loads(self.preferences_file.read_text(encoding="utf-8"))

    def get_events(self) -> list[dict[str, Any]]:
        events = []
        if self.memories_file.exists():
            with self.memories_file.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
        return events

    def remove_preference(self, pref_id: str) -> bool:
        data = self.get_preferences()
        if pref_id in data:
            del data[pref_id]
            self.preferences_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True
        return False
        
    def remove_identity(self, fact_id: str) -> bool:
        data = self.get_identities()
        if fact_id in data:
            del data[fact_id]
            self.identity_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True
        return False

    def remove_event(self, event_id: str) -> bool:
        events = self.get_events()
        found = False
        new_events = []
        for record in events:
            if record["uuid"] == event_id:
                found = True
            else:
                new_events.append(record)
        if found:
            with self.memories_file.open("w", encoding="utf-8") as f:
                for record in new_events:
                    f.write(json.dumps(record) + "\n")
        return found


class SessionMemoryStore:
    """Temporary context for the current conversation."""
    def __init__(self, memory_dir: Path) -> None:
        self.session_file = memory_dir / "session.json"
        self._ensure_file()
        
    def _ensure_file(self) -> None:
        if not self.session_file.exists():
            self.session_file.write_text("{}", encoding="utf-8")

    def update_session(self, key: str, value: Any) -> None:
        data = json.loads(self.session_file.read_text(encoding="utf-8"))
        data[key] = {"value": value, "timestamp": time.time()}
        self.session_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        
    def get_active_session(self, expiry_seconds: float = 3600) -> dict[str, Any]:
        data = json.loads(self.session_file.read_text(encoding="utf-8"))
        now = time.time()
        active = {k: v["value"] for k, v in data.items() if now - v["timestamp"] < expiry_seconds}
        return active


class InMemoryConversationMemory(ConversationMemoryStore):
    """Small bounded memory used by v0.1 before persistent storage exists."""

    def __init__(self, max_messages: int) -> None:
        self._messages: deque[Message] = deque(maxlen=max_messages)

    def add(self, message: Message) -> None:
        """Add a message to bounded memory."""
        self._messages.append(message)

    def recent(self, *, limit: int | None = None) -> Sequence[Message]:
        """Return recent messages in chronological order."""
        messages = list(self._messages)
        if limit is None:
            return messages
        return messages[-limit:]

    def clear(self) -> None:
        """Clear conversation memory."""
        self._messages.clear()


class MemoryManager:
    """Coordinates memory access for the brain without exposing storage details."""

    def __init__(
        self, 
        store: ConversationMemoryStore, 
        tagger: MemoryTagger | None = None,
        memory_dir: Path | None = None,
        settings: Any = None
    ) -> None:
        self._store = store
        self._tagger = tagger
        
        # Load from settings if provided, else defaults
        self._memory_enabled = True
        self._auto_save = True
        self._retrieval_limit = 5
        
        if settings and hasattr(settings, "memory"):
            self._memory_enabled = settings.memory.memory_enabled
            self._auto_save = settings.memory.auto_save
            self._retrieval_limit = settings.memory.retrieval_limit

        self._memory_dir = memory_dir or Path("memory")
        self.long_term = LongTermMemoryStore(self._memory_dir)
        self.session = SessionMemoryStore(self._memory_dir)
        
        # State machine for deletions
        self.pending_deletion: dict[str, Any] | None = None

    def add_user_message(self, content: str, is_wake_word_triggered: bool = False) -> None:
        """Record a user message, and potentially extract permanent memories."""
        
        metadata: dict[str, Any] = {}
        if self._tagger:
            metadata = self._tagger.tag_input(content, is_wake_word_triggered)
            
            # Automatically save if configured
            if self._memory_enabled and self._auto_save and "memory_type" in metadata:
                mtype = metadata["memory_type"]
                mcontent = metadata["memory_content"]
                if mtype == "identity":
                    self.long_term.save_identity(mcontent)
                elif mtype == "preference":
                    self.long_term.save_preference(mcontent)
                elif mtype == "event":
                    self.long_term.save_event(mcontent)

        self._store.add(Message(role="user", content=content, metadata=metadata))

    def add_assistant_message(self, content: str) -> None:
        """Record an assistant message."""
        self._store.add(Message(role="assistant", content=content))

    def retrieve_context(self, query: str) -> list[str]:
        """Retrieve relevant context for the current query (naive overlap for now)."""
        if not self._memory_enabled:
            return []
            
        query_words = set(query.lower().split())
        results = []
        
        identities = self.long_term.get_identities()
        for v in identities.values():
            results.append((v["content"], v["timestamp"]))
            
        preferences = self.long_term.get_preferences()
        for v in preferences.values():
            results.append((v["content"], v["timestamp"]))
            
        events = self.long_term.get_events()
        for e in events:
            results.append((e["content"], e["timestamp"]))
            
        # Basic scoring: number of overlapping words
        scored_results = []
        for content, ts in results:
            content_words = set(content.lower().split())
            score = len(query_words & content_words)
            if score > 0 or query_words.intersection({"who", "what", "remember", "know", "list"}):
                scored_results.append((score, ts, content))
                
        # Sort by score desc, then timestamp desc
        scored_results.sort(key=lambda x: (x[0], x[1]), reverse=True)
        
        top = [item[2] for item in scored_results[:self._retrieval_limit]]
        return top

    def recent_messages(self, *, limit: int | None = None) -> Sequence[Message]:
        """Return recent conversation messages."""
        return self._store.recent(limit=limit)

    def clear(self) -> None:
        """Clear conversation memory."""
        self._store.clear()
