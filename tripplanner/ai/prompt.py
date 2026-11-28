from pathlib import Path
import json
from string import Template

from tripplanner.ai.context import BuiltContext
from tripplanner.models import PlanDraft

PROMPT_VERSION = "plan-v2"
PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "plan_v2.txt"


class PromptRenderer:
    def __init__(self, template_path: Path = PROMPT_PATH) -> None:
        self._template = Template(template_path.read_text(encoding="utf-8"))

    def render(self, context: BuiltContext, validation_feedback: str = "") -> str:
        return self._template.substitute(
            schema=json.dumps(PlanDraft.model_json_schema(), ensure_ascii=False, indent=2),
            context=context.serialized_data,
            validation_feedback=validation_feedback or "none",
        )
