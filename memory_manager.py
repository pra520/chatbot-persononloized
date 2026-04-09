"""
Memory Manager - Conversation History System
Maintains per-session chat history with sliding window to control token usage.
"""

import time
import logging
from collections import defaultdict
from typing import List, Dict

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Per-session conversation memory with automatic pruning.

    Why memory matters:
    - Without memory, each message is treated in isolation
    - User references ("What about the price I mentioned?") would be misunderstood
    - Multi-turn conversations feel natural and coherent

    Why limit turns:
    - More history = more tokens = higher API cost
    - Stale context from 20 turns ago can confuse the AI
    - 8 turns (16 messages) is the sweet spot for UX vs cost
    """

    def __init__(self, max_turns: int = 8):
        """
        Args:
            max_turns: Maximum user-assistant turn pairs to remember
        """
        self.max_turns = max_turns
        self._sessions: Dict[str, List[Dict]] = defaultdict(list)
        self._session_meta: Dict[str, Dict] = {}

    def add_turn(self, session_id: str, user_message: str, assistant_response: str):
        """
        Add a conversation turn to session memory.
        Automatically trims oldest turns when limit is exceeded.
        """
        turn = {
            "user": user_message,
            "assistant": assistant_response,
            "timestamp": int(time.time())
        }

        self._sessions[session_id].append(turn)

        # Keep only last N turns (sliding window)
        if len(self._sessions[session_id]) > self.max_turns:
            removed = self._sessions[session_id].pop(0)
            logger.debug(f"[{session_id}] Memory pruned oldest turn")

        # Update session metadata
        if session_id not in self._session_meta:
            self._session_meta[session_id] = {
                "created_at": int(time.time()),
                "total_turns": 0
            }
        self._session_meta[session_id]["total_turns"] += 1
        self._session_meta[session_id]["last_active"] = int(time.time())

    def get_history(self, session_id: str) -> List[Dict]:
        """
        Retrieve conversation history for a session.
        Returns list of {user, assistant, timestamp} dicts.
        """
        return self._sessions.get(session_id, [])

    def clear_session(self, session_id: str):
        """Clear all memory for a session (reset button)"""
        if session_id in self._sessions:
            del self._sessions[session_id]
        if session_id in self._session_meta:
            del self._session_meta[session_id]
        logger.info(f"[{session_id}] Memory cleared")

    def get_session_stats(self, session_id: str) -> Dict:
        """Return stats about a session's memory usage"""
        history = self.get_history(session_id)
        meta = self._session_meta.get(session_id, {})
        return {
            "current_turns": len(history),
            "max_turns": self.max_turns,
            "total_turns": meta.get("total_turns", 0),
            "created_at": meta.get("created_at"),
            "last_active": meta.get("last_active")
        }

    def get_active_sessions(self) -> List[str]:
        """List all active session IDs"""
        return list(self._sessions.keys())
