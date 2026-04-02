from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from local_calendar import fetch_upcoming_events as fetch_local_calendar_events


def _truncate(text: str, limit: int = 800) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


@dataclass
class ContextItem:
    title: str
    summary: str
    source: str
    timestamp: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class ContextProvider:
    """
    Mock cross-app context provider.
    The current app does not have Graph connectors yet, so this layer derives
    context from the active document, local search results, and simple mock data.
    """

    def get_context(
        self,
        user_input: str,
        active_window: str,
        doc_text: str | None = None,
        doc_path: str | None = None,
        rag_results: list[dict] | None = None,
    ) -> dict:
        documents = self.fetch_recent_docs(active_window, doc_text, doc_path, rag_results or [])
        emails = self.fetch_recent_emails(user_input, active_window)
        calendar = self.fetch_upcoming_events(user_input, active_window)

        return {
            "documents": [item.to_dict() for item in documents],
            "emails": [item.to_dict() for item in emails],
            "calendar": [item.to_dict() for item in calendar],
        }

    def fetch_recent_docs(
        self,
        active_window: str,
        doc_text: str | None,
        doc_path: str | None,
        rag_results: list[dict],
    ) -> list[ContextItem]:
        docs: list[ContextItem] = []

        if doc_path:
            docs.append(
                ContextItem(
                    title=Path(doc_path).name,
                    summary=_truncate(doc_text or "Active document detected"),
                    source="active_document",
                    metadata={"path": doc_path, "window": active_window},
                )
            )

        for result in rag_results[:3]:
            source = str(result.get("source", "local_doc"))
            docs.append(
                ContextItem(
                    title=Path(source).name or source,
                    summary=_truncate(str(result.get("content", "")), 300),
                    source="local_rag",
                    metadata={"path": source, "score": result.get("score")},
                )
            )

        return docs[:4]

    def fetch_recent_emails(self, user_input: str, active_window: str) -> list[ContextItem]:
        lower_window = (active_window or "").lower()
        lower_query = user_input.lower()
        email_app_hints = ("outlook", "mail", "gmail", "lark", "teams")
        email_query_hints = ("email", "mail", "reply", "client")
        if not any(token in lower_window for token in email_app_hints) and not any(token in lower_query for token in email_query_hints):
            return []

        return [
            ContextItem(
                title="Client follow-up thread",
                summary="Mock email context: client asked for next steps and timeline confirmation.",
                source="mock_email",
                timestamp=(datetime.now() - timedelta(minutes=18)).isoformat(timespec="minutes"),
                metadata={"sender": "client@example.com", "priority": "high"},
            )
        ]

    def fetch_upcoming_events(self, user_input: str, active_window: str) -> list[ContextItem]:
        lower_window = (active_window or "").lower()
        lower_query = user_input.lower()
        calendar_app_hints = ("calendar", "lark", "outlook", "teams", "google calendar")
        calendar_query_hints = ("meeting", "calendar", "prep", "sync", "agenda")
        if not any(token in lower_window for token in calendar_app_hints) and not any(token in lower_query for token in calendar_query_hints):
            return []

        real_events = fetch_local_calendar_events(limit=3, lookahead_hours=24)
        if real_events:
            return [
                ContextItem(
                    title=event.title,
                    summary=f"Upcoming event from {event.calendar_name}" + (f" at {event.location}" if event.location else ""),
                    source="local_calendar",
                    timestamp=event.start_text,
                    metadata={
                        "calendar_name": event.calendar_name,
                        "location": event.location,
                        "starts_in_minutes": event.starts_in_minutes,
                    },
                )
                for event in real_events
            ]

        return []
