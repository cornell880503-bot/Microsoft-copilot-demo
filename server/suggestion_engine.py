from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from query_normalizer import normalize_query


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

    def preset_suggestions_for_window(self, active_window: str) -> list[Suggestion]:
        window = normalize_query(active_window)

        app_presets: list[tuple[tuple[str, ...], list[Suggestion]]] = [
            (
                ("lark", "feishu"),
                [
                    Suggestion("meeting_prep", "Prepare for my next meeting", "generate_meeting_brief", 0.94, "Lark/Feishu collaboration surface detected."),
                    Suggestion("message_summary", "Summarize my latest messages", "summarize_recent_messages", 0.88, "Messaging workflow detected."),
                    Suggestion("reply_draft", "Draft a quick follow-up reply", "draft_client_reply", 0.84, "Collaboration app detected."),
                ],
            ),
            (
                ("calendar", "google calendar", "outlook calendar"),
                [
                    Suggestion("meeting_lookup", "When is my next meeting today", "lookup_next_meeting", 0.96, "Calendar surface detected."),
                    Suggestion("meeting_prep", "Prepare for my next meeting", "generate_meeting_brief", 0.92, "Calendar surface detected."),
                    Suggestion("agenda_summary", "Summarize today's schedule", "summarize_schedule", 0.82, "Calendar surface detected."),
                ],
            ),
            (
                ("outlook", "mail", "gmail"),
                [
                    Suggestion("inbox_summary", "Summarize my latest emails", "summarize_recent_messages", 0.92, "Email surface detected."),
                    Suggestion("reply_draft", "Draft a reply to the latest email", "draft_client_reply", 0.88, "Email surface detected."),
                    Suggestion("followup", "List follow-ups from this inbox", "extract_followups", 0.8, "Email surface detected."),
                ],
            ),
            (
                ("docs", "google docs", "word", "pages"),
                [
                    Suggestion("doc_summary", "Summarize this document", "summarize_active_document", 0.9, "Document editor detected."),
                    Suggestion("rewrite", "Rewrite this more clearly", "rewrite_content", 0.84, "Document editor detected."),
                    Suggestion("action_items", "Extract action items from this", "extract_action_items", 0.8, "Document editor detected."),
                ],
            ),
            (
                ("sheets", "excel", "numbers", "csv"),
                [
                    Suggestion("analysis", "Analyze this data with Python", "execute_python_analysis", 0.92, "Spreadsheet surface detected."),
                    Suggestion("summary", "Summarize key metrics here", "summarize_metrics", 0.86, "Spreadsheet surface detected."),
                    Suggestion("chart", "Suggest a chart for this data", "suggest_chart", 0.78, "Spreadsheet surface detected."),
                ],
            ),
        ]

        for aliases, suggestions in app_presets:
            if any(alias in window for alias in aliases):
                return suggestions[:3]
        return []

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
