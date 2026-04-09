"""
Context Store - Document Knowledge Base Management
Manages per-session document contexts for AI injection.
"""

import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Maximum total context size to inject into AI (characters)
MAX_CONTEXT_CHARS = 6000


class ContextStore:
    """
    Per-session document context storage.

    Each session can upload multiple documents.
    All documents are combined into a unified context string
    that gets injected into the AI system prompt.

    Design decisions:
    - In-memory storage (for simplicity; use Redis/DB for production scale)
    - Per-session isolation ensures different clients don't bleed data
    - Context is trimmed to MAX_CONTEXT_CHARS to prevent token overflow
    """

    def __init__(self):
        # session_id → {filename: context_string}
        self._documents: Dict[str, Dict[str, str]] = defaultdict(dict)
        self._upload_times: Dict[str, Dict[str, int]] = defaultdict(dict)

    def add_document(self, session_id: str, filename: str, context: str):
        """
        Store processed document context for a session.
        If same filename is uploaded again, it replaces the old one.
        """
        self._documents[session_id][filename] = context
        self._upload_times[session_id][filename] = int(time.time())
        logger.info(f"[{session_id}] Context added: {filename} ({len(context)} chars)")

    def get_context(self, session_id: str) -> str:
        """
        Build unified context string for AI injection.

        Combines all uploaded documents for this session.
        Trims to MAX_CONTEXT_CHARS to stay within token limits.
        """
        docs = self._documents.get(session_id, {})
        if not docs:
            return ""

        # Combine all document contexts
        parts = []
        for filename, context in docs.items():
            parts.append(f"[Source: {filename}]\n{context}")

        combined = "\n\n".join(parts)

        # Trim if too large
        if len(combined) > MAX_CONTEXT_CHARS:
            logger.warning(
                f"[{session_id}] Context trimmed from {len(combined)} to {MAX_CONTEXT_CHARS} chars"
            )
            combined = combined[:MAX_CONTEXT_CHARS] + "\n\n[Context trimmed due to size limits]"

        return combined

    def remove_document(self, session_id: str, filename: str) -> bool:
        """Remove a specific document from session context"""
        if session_id in self._documents and filename in self._documents[session_id]:
            del self._documents[session_id][filename]
            if filename in self._upload_times.get(session_id, {}):
                del self._upload_times[session_id][filename]
            logger.info(f"[{session_id}] Document removed: {filename}")
            return True
        return False

    def clear_session(self, session_id: str):
        """Remove all documents for a session"""
        if session_id in self._documents:
            del self._documents[session_id]
        if session_id in self._upload_times:
            del self._upload_times[session_id]
        logger.info(f"[{session_id}] Context cleared")

    def list_documents(self, session_id: str) -> List[Dict]:
        """Return metadata about uploaded documents"""
        docs = self._documents.get(session_id, {})
        times = self._upload_times.get(session_id, {})
        return [
            {
                "filename": fname,
                "size_chars": len(ctx),
                "uploaded_at": times.get(fname, 0)
            }
            for fname, ctx in docs.items()
        ]

    def has_context(self, session_id: str) -> bool:
        """Check if session has any uploaded documents"""
        return bool(self._documents.get(session_id))
