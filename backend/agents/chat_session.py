from backend.services.llm_router import generate, generate_stream
from backend.services.archivist import (
    search_themes_smart,
    search_sutras_smart,
    search_talking_points,
    search_poses_smart,
)
from backend.prompts.theme_explanation import THEME_SYSTEM_PROMPT
from typing import Generator


class ChatSession:
    def __init__(self):
        self.history: list[dict] = []
        self.current_flow: dict | None = None
        self.mode: str = "fast"
        self.context_type: str = "Both"
        self.allow_flow_edits: bool = False

    def set_mode(self, mode: str):
        self.mode = mode

    def set_flow(self, flow: dict):
        self.current_flow = flow

    def set_flow_edit_mode(self, allow: bool):
        self.allow_flow_edits = allow

    def set_history(self, history: list[dict]):
        if not isinstance(history, list):
            return
        sanitized = []
        for item in history:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content", "")
            if role not in {"user", "assistant"}:
                continue
            if not isinstance(content, str):
                continue
            sanitized.append({"role": role, "content": content})
        self.history = sanitized

    def _is_flow_edit_request(self, message: str) -> bool:
        msg = (message or "").lower()
        keywords = [
            "add",
            "remove",
            "move",
            "replace",
            "swap",
            "substitute",
            "switch",
            "insert",
            "reorder",
            "build",
            "create",
            "make",
            "flow",
            "sequence",
            "section",
            "pose",
            "poses",
            "warm up",
            "warmup",
            "peak",
            "cool down",
            "cooldown",
            "savasana",
            "shavasana",
        ]
        return any(k in msg for k in keywords)

    def build_context(self, query: str) -> str:
        context_parts = []

        pose_results = search_poses_smart(query, limit=12)
        if pose_results:
            pose_lines = []
            for r in pose_results:
                name = r.get("metadata", {}).get("name")
                doc = r.get("document", "")
                pose_lines.append(f"- {name or doc}")
            context_parts.append("Relevant poses:\n" + "\n".join(pose_lines))

        theme_results = search_themes_smart(query, limit=6)
        if theme_results:
            theme_lines = []
            for r in theme_results:
                name = r.get("metadata", {}).get("name")
                doc = r.get("document", "")
                theme_lines.append(f"- {name or doc}")
            context_parts.append("Related themes:\n" + "\n".join(theme_lines))

        sutra_results = search_sutras_smart(query, limit=6)
        if sutra_results:
            sutra_lines = []
            for r in sutra_results:
                doc = r.get("document", "")
                sutra_lines.append(f"- {doc}")
            context_parts.append("Relevant sutras:\n" + "\n".join(sutra_lines))

        talking_point_results = search_talking_points(query, limit=6)
        if talking_point_results:
            tp_lines = []
            for r in talking_point_results:
                doc = r.get("document", "")
                tp_lines.append(f"- {doc}")
            context_parts.append("Related talking points:\n" + "\n".join(tp_lines))

        total_hits = (
            len(pose_results) + len(theme_results) + len(sutra_results) + len(talking_point_results)
        )
        if total_hits < 3:
            context_parts.insert(0, "Match quality: weak (few or indirect library matches).")

        if self.current_flow and self.allow_flow_edits:
            flow_name = self.current_flow.get("flow_name", "Untitled")
            sections = self.current_flow.get("sections") or []
            section_summaries = []
            for section in sections[:8]:
                label = section.get("label", "Section")
                blocks = section.get("blocks") or []
                block_names = []
                for block in blocks[:8]:
                    name = (
                        block.get("pose_name")
                        or block.get("description")
                        or block.get("block_type", "block")
                    )
                    block_names.append(name)
                if block_names:
                    section_summaries.append(f"{label}: " + ", ".join(block_names))
                else:
                    section_summaries.append(f"{label}: (empty)")
            flow_summary = f"Current flow: {flow_name}\n" + "\n".join(section_summaries)
            context_parts.append(flow_summary)

        return "\n\n".join(context_parts)

    def chat(self, message: str) -> str:
        self.history.append({"role": "user", "content": message})
        context = self.build_context(message)
        system = THEME_SYSTEM_PROMPT
        if self.allow_flow_edits:
            system += (
                "\n\nIf the user explicitly asks you to edit or build a flow, include a machine-readable plan in a "
                "```flow_changes``` code block. The JSON must follow this shape:\n"
                '{"operations":[{"type":"add_pose","pose":"English Pose Name","section":"Section Label (optional)",'
                '"position":"start|middle|end (optional)"}]}\n'
                'You may also use type "remove_pose", "move_pose", or "replace_pose" with fields:\n'
                '- remove_pose: {"pose":"English Pose Name","section":"Section Label (optional)"}\n'
                '- move_pose: {"pose":"English Pose Name","from_section":"Label (optional)","to_section":"Label (optional)",'
                '"position":"start|middle|end (optional)"}\n'
                '- replace_pose: {"from_pose":"English Pose Name","to_pose":"English Pose Name","section":"Label (optional)"}\n'
                "Only include this block when the user asks to modify the flow. Keep the rest of the response short."
            )
            if self._is_flow_edit_request(message):
                system += "\n\nIMPORTANT: This is a flow edit request. You MUST include a ```flow_changes``` block."
        if context:
            system += f"\n\nContext:\n{context}"
        full_prompt = "\n".join(f"{m['role']}: {m['content']}" for m in self.history[-6:])
        response = generate(full_prompt, mode=self.mode, system=system)
        self.history.append({"role": "assistant", "content": response})
        return response

    def chat_stream(self, message: str) -> Generator[str, None, None]:
        self.history.append({"role": "user", "content": message})
        context = self.build_context(message)
        system = THEME_SYSTEM_PROMPT
        if self.allow_flow_edits:
            system += (
                "\n\nIf the user explicitly asks you to edit or build a flow, include a machine-readable plan in a "
                "```flow_changes``` code block. The JSON must follow this shape:\n"
                '{"operations":[{"type":"add_pose","pose":"English Pose Name","section":"Section Label (optional)",'
                '"position":"start|middle|end (optional)"}]}\n'
                'You may also use type "remove_pose", "move_pose", or "replace_pose" with fields:\n'
                '- remove_pose: {"pose":"English Pose Name","section":"Section Label (optional)"}\n'
                '- move_pose: {"pose":"English Pose Name","from_section":"Label (optional)","to_section":"Label (optional)",'
                '"position":"start|middle|end (optional)"}\n'
                '- replace_pose: {"from_pose":"English Pose Name","to_pose":"English Pose Name","section":"Label (optional)"}\n'
                "Only include this block when the user asks to modify the flow. Keep the rest of the response short."
            )
            if self._is_flow_edit_request(message):
                system += "\n\nIMPORTANT: This is a flow edit request. You MUST include a ```flow_changes``` block."
        if context:
            system += f"\n\nContext:\n{context}"
        full_prompt = "\n".join(f"{m['role']}: {m['content']}" for m in self.history[-6:])
        full_response = ""
        for chunk in generate_stream(full_prompt, mode=self.mode, system=system):
            full_response += chunk
            yield chunk
        self.history.append({"role": "assistant", "content": full_response})
