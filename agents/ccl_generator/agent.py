"""CCL Generator Agent — generates CCL XML from extracted intents."""

from __future__ import annotations

import json
import logging

from agents.base import BaseComplianceAgent
from contracts.ccl_contract import CCLInput, CCLOutput
from explainability.collector import TraceCollector
from explainability.trace import TraceNodeType
from infrastructure.llm_provider import AbstractLLMProvider

from .prompts import CCL_SYSTEM_PROMPT, CCL_USER_PROMPT

logger = logging.getLogger(__name__)


class CCLGeneratorAgent(BaseComplianceAgent[CCLInput, CCLOutput]):
    """Generates CCL XML documents from extracted compliance intents."""

    name = "ccl_generator"

    def __init__(self, slm_service):
        super().__init__(slm_service=slm_service)

    async def execute(self, input: CCLInput, trace: TraceCollector) -> CCLOutput:
        """Generate CCL XML from intents using LLM."""
        intents_json = json.dumps(
            [i.model_dump() for i in input.intents], indent=2
        )

        prompt = CCL_USER_PROMPT.format(
            regulation_id=input.regulation_id,
            regulation_title=input.regulation_title or "Unknown Regulation",
            regulation_text=input.regulation_text,
            intents_json=intents_json,
        )

        async with trace.span(
            "llm_ccl_generation", TraceNodeType.LLM_CALL, agent_name=self.name
        ) as span:
            span.set_input(f"{len(input.intents)} intents")

            response = await self._slm_service.query(
                prompt=prompt,
                system_prompt=CCL_SYSTEM_PROMPT,
                temperature=0.0,
                max_tokens=8192,
                use_rag=True,
                rag_query=input.regulation_title or input.regulation_text[:200]
            )

            ccl_xml = self._extract_xml(response)
            span.set_output(f"Generated CCL XML ({len(ccl_xml)} chars)")

        # Validate structure
        async with trace.span(
            "validate_ccl_structure", TraceNodeType.VALIDATION, agent_name=self.name
        ) as span:
            validation_errors = self._validate_basic_structure(ccl_xml)
            clause_count = ccl_xml.count("<ccl:clause") or ccl_xml.count("<clause")
            constraint_count = ccl_xml.count("<ccl:constraint") or ccl_xml.count("<constraint")
            probe_count = ccl_xml.count("<ccl:probe-strategy") or ccl_xml.count("<probe-strategy")

            span.set_output(
                f"clauses={clause_count}, constraints={constraint_count}, probes={probe_count}"
            )
            if validation_errors:
                span.set_confidence(0.6, ["structural_issues_found"])
            else:
                span.set_confidence(0.9, ["valid_structure"])

        return CCLOutput(
            metadata=input.metadata,
            success=len(validation_errors) == 0,
            ccl_xml=ccl_xml,
            clause_count=clause_count,
            constraint_count=constraint_count,
            probe_strategy_count=probe_count,
            validation_errors=validation_errors,
            state_updates={"ccl_document": ccl_xml},
        )

    def _extract_xml(self, content: str) -> str:
        """Extract XML from LLM response (may be wrapped in markdown)."""
        content = content.strip()
        if content.startswith("```xml"):
            content = content[6:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    def _validate_basic_structure(self, xml: str) -> list[str]:
        """Basic structural validation of CCL XML."""
        errors = []
        if not xml:
            errors.append("Empty CCL document")
            return errors

        if "ccl:" not in xml and "<regulation" not in xml:
            errors.append("Missing CCL namespace or regulation element")

        required_elements = ["constraint", "threshold", "measure"]
        for element in required_elements:
            if element not in xml.lower():
                errors.append(f"Missing required element: {element}")

        return errors
