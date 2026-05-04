from backend.services.llm_router import generate
from backend.services.archivist import get_theme_context
from backend.services.vector_store import search, collection_exists
from backend.prompts.flow_generation import FLOW_GENERATION_PROMPT, FLOW_MODIFICATION_PROMPT
import json


class FlowAgent:
    def __init__(self):
        self.data_available = collection_exists("poses")

    def generate_flow_suggestion(self, constraints: dict) -> dict:
        duration = constraints.get("duration", 60)
        context_type = constraints.get("context_type", "IRL")
        theme = constraints.get("theme", "")
        energy_level = constraints.get("energy_level", "moderate")
        context = ""
        if theme:
            context = get_theme_context(theme)
        if self.data_available:
            pose_results = search("poses", f"{energy_level} yoga poses", n_results=10)
            context += "\n\nAvailable poses:\n" + "\n".join(
                f"- {r['document']}" for r in pose_results
            )
        prompt = FLOW_GENERATION_PROMPT.format(
            duration=duration,
            context_type=context_type,
            theme=theme or "general practice",
            energy_level=energy_level,
            context=context,
        )
        response = generate(prompt, mode="power")
        return self._parse_flow_response(response, constraints)

    def suggest_modification(self, current_flow: dict, request: str) -> dict:
        prompt = FLOW_MODIFICATION_PROMPT.format(
            current_flow=json.dumps(current_flow, indent=2), request=request
        )
        response = generate(prompt, mode="fast")
        return {"suggestion": response, "original": current_flow}

    def _parse_flow_response(self, response: str, constraints: dict) -> dict:
        sections = [
            {
                "label": "Centering",
                "blocks": [
                    {"block_type": "custom", "description": "Opening meditation", "duration": 180}
                ],
            },
            {"label": "Warm Up", "blocks": []},
            {"label": "Sun Salutations", "blocks": []},
            {"label": "Standing", "blocks": []},
            {"label": "Peak", "blocks": []},
            {"label": "Floor", "blocks": []},
            {"label": "Cool Down", "blocks": []},
            {
                "label": "Savasana",
                "blocks": [
                    {"block_type": "custom", "description": "Final relaxation", "duration": 300}
                ],
            },
        ]
        return {
            "flow_name": f"{constraints.get('theme', 'Flow')} - {constraints.get('duration', 60)} min",
            "description": response[:500],
            "context_type": constraints.get("context_type", "Both"),
            "blocks_json": json.dumps(sections),
            "ai_response": response,
        }
