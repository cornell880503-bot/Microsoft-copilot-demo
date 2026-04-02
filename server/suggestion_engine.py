from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Suggestion:
    type: str
    text: str
    action: str
    relevance_score: float
    reason: str
    dismissible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "text": self.text,
            "action": self.action,
            "relevance_score": self.relevance_score,
            "reason": self.reason,
            "dismissible": self.dismissible,
        }


class SuggestionEngine:
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold

    def detect_triggers(self, user_input: str, context: dict) -> list[str]:
        triggers: list[str] = []

        calendar = context.get("calendar", [])
        emails = context.get("emails", [])
        documents = context.get("documents", [])
        query = user_input.lower()

        if any((item.get("metadata") or {}).get("starts_in_minutes", 999) <= 10 for item in calendar):
            triggers.append("pre_meeting")
        if emails and (not query or any(token in query for token in ("email", "reply", "follow up", "client"))):
            triggers.append("email_followup")
        elif emails:
            triggers.append("inbox_context")
        if len(documents) >= 2:
            triggers.append("document_focus")

        return triggers

    def generate_suggestions(self, triggers: list[str], context: dict) -> list[Suggestion]:
        suggestions: list[Suggestion] = []

        if "pre_meeting" in triggers:
            suggestions.append(
                Suggestion(
                    type="meeting_prep",
                    text="Prepare talking points for your meeting",
                    action="generate_meeting_brief",
                    relevance_score=0.92,
                    reason="Upcoming meeting detected in calendar context.",
                )
            )
        if "email_followup" in triggers:
            suggestions.append(
                Suggestion(
                    type="email_draft",
                    text="Draft a reply to the client",
                    action="draft_client_reply",
                    relevance_score=0.86,
                    reason="Recent email context suggests a follow-up task.",
                )
            )
        if "inbox_context" in triggers:
            suggestions.append(
                Suggestion(
                    type="email_summary",
                    text="Summarize your latest messages",
                    action="summarize_recent_messages",
                    relevance_score=0.72,
                    reason="Mail or collaboration context is active.",
                )
            )
        if "document_focus" in triggers:
            suggestions.append(
                Suggestion(
                    type="doc_summary",
                    text="Summarize the active document",
                    action="summarize_active_document",
                    relevance_score=0.68,
                    reason="The user appears to be working repeatedly across related docs.",
                )
            )

        filtered = [s for s in suggestions if s.relevance_score >= self.threshold]
        filtered.sort(key=lambda item: item.relevance_score, reverse=True)
        return filtered[:3]

    def decide_mode(self, suggestions: list[Suggestion]) -> str:
        return "proactive" if suggestions else "reactive"
