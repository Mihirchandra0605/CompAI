"""Skill Generator Agent — derives executable probe definitions from CCL ProbeStrategies."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from agents.base import BaseComplianceAgent
from contracts.base import AgentInput, AgentOutput
from contracts.probe_contract import ProbeDefinition
from explainability.collector import TraceCollector
from explainability.trace import TraceNodeType
from pydantic import Field

logger = logging.getLogger(__name__)


class SkillGeneratorInput(AgentInput):
    """Input for the Skill Generator."""

    ccl_document: str
    regulation_id: str


class SkillGeneratorOutput(AgentOutput):
    """Output from the Skill Generator."""

    probe_definitions: list[ProbeDefinition] = Field(default_factory=list)
    validation_conditions: list[dict[str, Any]] = Field(default_factory=list)


class SkillGeneratorAgent(BaseComplianceAgent[SkillGeneratorInput, SkillGeneratorOutput]):
    """
    Derives executable probe definitions and validation conditions from CCL.

    This agent bridges CCL ProbeStrategies (WHAT to collect)
    to ProbeDefinitions (HOW to collect it).
    """

    name = "skill_generator"

    async def execute(
        self, input: SkillGeneratorInput, trace: TraceCollector
    ) -> SkillGeneratorOutput:
        """Derive probe definitions from CCL document."""
        from ccl.parser import CCLParser

        async with trace.span(
            "parse_ccl_for_probes", TraceNodeType.TOOL_USE, agent_name=self.name
        ) as span:
            parser = CCLParser()
            try:
                doc = parser.parse(input.ccl_document)
            except ValueError as e:
                span.set_output(f"Parse error: {e}")
                return SkillGeneratorOutput(
                    metadata=input.metadata, success=False, state_updates={}
                )
            span.set_output("CCL parsed successfully")

        async with trace.span(
            "derive_probe_definitions", TraceNodeType.INFERENCE, agent_name=self.name
        ) as span:
            probe_defs: list[ProbeDefinition] = []
            validation_conditions: list[dict[str, Any]] = []
            run_id = input.metadata.run_id

            if doc.regulation:
                for clause in doc.regulation.clauses:
                    for intent in clause.intents:
                        for obj in intent.objectives:
                            for con in obj.constraints:
                                # Derive probe definition from evidence requirements
                                if con.evidence_requirement:
                                    for ps in con.evidence_requirement.probe_strategies:
                                        probe_def = self._derive_probe(
                                            ps, con, doc, run_id
                                        )
                                        probe_defs.append(probe_def)

                                # Derive validation condition from constraint
                                if con.threshold and con.measure:
                                    vc = self._derive_validation_condition(con)
                                    validation_conditions.append(vc)

            span.set_output(
                f"Derived {len(probe_defs)} probes, {len(validation_conditions)} conditions"
            )
            span.set_confidence(0.9, ["deterministic_derivation"])

        return SkillGeneratorOutput(
            metadata=input.metadata,
            success=True,
            probe_definitions=probe_defs,
            validation_conditions=validation_conditions,
            state_updates={
                "probe_definitions": [pd.model_dump() for pd in probe_defs],
            },
        )

    def _derive_probe(self, ps, constraint, doc, run_id: str) -> ProbeDefinition:
        """Derive a ProbeDefinition from a CCL ProbeStrategy."""
        # Find target system location
        target_location = ""
        for ts in doc.target_systems:
            if ts.system_id == ps.target_system_ref:
                target_location = ts.location
                break

        # Build config based on probe type
        config: dict[str, Any] = {
            "file_path": target_location,
            "method": ps.method,
        }

        if constraint.measure:
            config["aggregation"] = {
                "method": constraint.measure.aggregation.lower(),
                "column": constraint.measure.name,
            }

        if constraint.threshold:
            config["filter"] = {}
            if constraint.threshold.window:
                config["window"] = constraint.threshold.window

        return ProbeDefinition(
            probe_id=f"probe:{run_id[:8]}:{uuid.uuid4().hex[:8]}",
            derived_from=ps.strategy_id,
            probe_type=ps.probe_type,
            config=config,
        )

    def _derive_validation_condition(self, constraint) -> dict[str, Any]:
        """Derive a ValidationCondition from a CCL Constraint."""
        vc_type = "DETERMINISTIC"
        if constraint.validation_condition:
            vc_type = constraint.validation_condition.condition_type

        return {
            "condition_id": f"vc:{constraint.constraint_id}",
            "constraint_id": constraint.constraint_id,
            "condition_type": vc_type,
            "measure_name": constraint.measure.name if constraint.measure else "",
            "operator": constraint.threshold.operator if constraint.threshold else "LTE",
            "threshold_value": constraint.threshold.value if constraint.threshold else 0.0,
            "threshold_unit": constraint.threshold.unit if constraint.threshold else "",
            "aggregation": constraint.measure.aggregation if constraint.measure else "MEAN",
            "window": constraint.threshold.window if constraint.threshold else None,
            "min_samples": constraint.threshold.min_samples if constraint.threshold else 100,
        }
