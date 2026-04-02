from __future__ import annotations

from pathlib import Path


class PromptBuilder:
    def select_context(self, user_input: str, context: dict) -> tuple[dict, list[str]]:
        query = user_input.lower()

        if "meeting" in query:
            keys = ["calendar", "documents"]
        elif "email" in query or "reply" in query or "mail" in query:
            keys = ["emails", "documents"]
        else:
            keys = ["documents"]

        selected = {}
        used = []
        for key in keys:
            items = context.get(key, []) or []
            if items:
                selected[key] = items[:3]
                used.append(key)

        if not selected:
            return {"documents": []}, []
        return selected, used

    def build_augmented_prompt(
        self,
        user_input: str,
        active_window: str,
        context: dict,
        memory: dict,
        rag_results: list[dict],
        doc_text: str | None = None,
        doc_path: str | None = None,
    ) -> dict:
        selected_context, context_used = self.select_context(user_input, context)

        memory_lines = []
        if memory.get("tone"):
            memory_lines.append(f"- Tone: {memory['tone']}")
        if memory.get("format"):
            memory_lines.append(f"- Format: {memory['format']}")
        memory_block = "\n".join(memory_lines) if memory_lines else "- None saved"

        doc_section = self._build_document_section(doc_text, doc_path)
        rag_section = self._build_rag_section(rag_results)
        context_section = self._build_context_section(selected_context)

        augmented_prompt = (
            "You are an AI Copilot embedded in the user's workflow.\n\n"
            f"Active Application:\n{active_window or 'Unknown'}\n\n"
            f"User Preferences:\n{memory_block}\n\n"
            f"Context:\n{context_section}\n"
            f"{doc_section}"
            f"{rag_section}\n"
            f"User Request:\n{user_input}\n\n"
            "Generate actionable output."
        )

        return {
            "augmented_prompt": augmented_prompt,
            "context_used": context_used,
        }

    def _build_context_section(self, context: dict) -> str:
        if not context:
            return "No relevant cross-app context available."

        lines = []
        for key in ("documents", "emails", "calendar"):
            items = context.get(key, []) or []
            if not items:
                continue
            lines.append(f"{key.title()}:")
            for item in items:
                title = item.get("title", "Untitled")
                summary = item.get("summary", "")
                lines.append(f"- {title}: {summary}")

        return "\n".join(lines) if lines else "No relevant cross-app context available."

    def _build_document_section(self, doc_text: str | None, doc_path: str | None) -> str:
        if not doc_path:
            return ""

        fname = Path(doc_path).name
        ext = Path(doc_path).suffix.lower()
        if doc_text and ext not in (".csv", ".xlsx", ".xls"):
            return f"\n\nActive Document — {fname} (path: {doc_path}):\n{doc_text}"
        if doc_text:
            preview = "\n".join(doc_text.splitlines()[:8])
            return (
                f"\n\nActive Document — {fname}\n"
                f"Full file path (use this in code): {doc_path}\n"
                f"File preview (first 8 rows):\n{preview}\n"
                "NOTE: Always read the file from DOC_PATH when generating code."
            )
        return f"\n\nActive Document path: {doc_path}"

    def _build_rag_section(self, rag_results: list[dict]) -> str:
        if not rag_results:
            return ""
        excerpts = "\n---\n".join(
            f"[source: {r['source']}, score: {r['score']:.3f}]\n{r['content']}"
            for r in rag_results
        )
        return f"\n\nLocal Knowledge Base Results:\n{excerpts}"

