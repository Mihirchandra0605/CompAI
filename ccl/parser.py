"""CCL XML Parser — parses CCL documents into structured Python objects."""

from __future__ import annotations

import logging
from typing import Any
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# CCL namespace
CCL_NS = "urn:compliai:ccl:v1"
QOS_NS = "urn:compliai:ccl:ext:qos:v1"
NAMESPACES = {"ccl": CCL_NS, "qos": QOS_NS}


class CCLMeasure(BaseModel):
    name: str
    unit: str
    data_type: str = "FLOAT"
    aggregation: str = "MEAN"


class CCLThreshold(BaseModel):
    operator: str
    value: float
    unit: str
    tolerance: float = 0.0
    window: str | None = None
    min_samples: int = 100


class CCLValidationCondition(BaseModel):
    condition_type: str = "DETERMINISTIC"
    predicate: str = ""
    confidence_base: float = 0.99


class CCLProbeStrategy(BaseModel):
    strategy_id: str
    probe_type: str
    method: str = ""
    output_format: str = ""
    target_system_ref: str = ""


class CCLEvidenceRequirement(BaseModel):
    requirement_id: str
    evidence_type: str
    freshness: str = "PT24H"
    probe_strategies: list[CCLProbeStrategy] = Field(default_factory=list)


class CCLConstraint(BaseModel):
    constraint_id: str
    constraint_type: str
    description: str = ""
    measure: CCLMeasure | None = None
    threshold: CCLThreshold | None = None
    evidence_requirement: CCLEvidenceRequirement | None = None
    validation_condition: CCLValidationCondition | None = None


class CCLObjective(BaseModel):
    objective_id: str
    description: str = ""
    logic: str = "AND"
    constraints: list[CCLConstraint] = Field(default_factory=list)


class CCLIntent(BaseModel):
    intent_id: str
    description: str = ""
    category: str = ""
    objectives: list[CCLObjective] = Field(default_factory=list)


class CCLRisk(BaseModel):
    risk_type: str = "OPERATIONAL"
    severity: str = "MEDIUM"
    consequence: str = ""


class CCLClause(BaseModel):
    clause_id: str
    section_ref: str = ""
    text: str = ""
    obligation: str = "MANDATORY"
    risk: CCLRisk | None = None
    intents: list[CCLIntent] = Field(default_factory=list)


class CCLTargetSystem(BaseModel):
    system_id: str
    system_type: str
    access_method: str
    location: str = ""


class CCLRegulation(BaseModel):
    regulation_id: str
    title: str = ""
    authority: str = ""
    jurisdiction: str = ""
    version: str = ""
    effective_date: str = ""
    clauses: list[CCLClause] = Field(default_factory=list)


class CCLDocument(BaseModel):
    """Parsed CCL document — structured representation."""

    ccl_version: str = "1.0"
    schema_version: str = "urn:compliai:ccl:v1"
    generated_by: str = ""
    target_systems: list[CCLTargetSystem] = Field(default_factory=list)
    regulation: CCLRegulation | None = None


class CCLParser:
    """Parses CCL XML into structured CCLDocument objects."""

    def parse(self, xml_string: str) -> CCLDocument:
        """Parse a CCL XML string into a CCLDocument."""
        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")

        document = CCLDocument()

        # Parse metadata
        metadata = self._find(root, "metadata")
        if metadata is not None:
            version_el = self._find(metadata, "version")
            if version_el is not None and version_el.text:
                document.ccl_version = version_el.text
            gen_el = self._find(metadata, "generated-by")
            if gen_el is not None:
                document.generated_by = gen_el.get("agent", "")

        # Parse target systems
        ts_container = self._find(root, "target-systems")
        if ts_container is not None:
            for ts_el in self._findall(ts_container, "target-system"):
                document.target_systems.append(self._parse_target_system(ts_el))

        # Parse regulation
        reg_el = self._find(root, "regulation")
        if reg_el is not None:
            document.regulation = self._parse_regulation(reg_el)

        return document

    def parse_file(self, file_path: str) -> CCLDocument:
        """Parse a CCL XML file."""
        from pathlib import Path
        content = Path(file_path).read_text()
        return self.parse(content)

    def _parse_regulation(self, el: ET.Element) -> CCLRegulation:
        reg = CCLRegulation(
            regulation_id=el.get("id", ""),
            title=self._text(el, "title"),
            authority=self._text(el, "authority"),
            jurisdiction=self._text(el, "jurisdiction"),
            version=self._text(el, "reg-version"),
            effective_date=self._text(el, "effective-date"),
        )
        for clause_el in self._findall(el, "clause"):
            reg.clauses.append(self._parse_clause(clause_el))
        return reg

    def _parse_clause(self, el: ET.Element) -> CCLClause:
        clause = CCLClause(
            clause_id=el.get("id", ""),
            section_ref=el.get("section-ref", ""),
            text=self._text(el, "text"),
            obligation=self._text(el, "obligation"),
        )
        # Parse risk
        risk_el = self._find(el, "risk")
        if risk_el is not None:
            clause.risk = CCLRisk(
                risk_type=self._text(risk_el, "risk-type"),
                severity=self._text(risk_el, "severity"),
                consequence=self._text(risk_el, "consequence"),
            )
        # Parse intents
        for intent_el in self._findall(el, "intent"):
            clause.intents.append(self._parse_intent(intent_el))
        return clause

    def _parse_intent(self, el: ET.Element) -> CCLIntent:
        intent = CCLIntent(
            intent_id=el.get("id", ""),
            description=self._text(el, "description"),
            category=self._text(el, "category"),
        )
        for obj_el in self._findall(el, "objective"):
            intent.objectives.append(self._parse_objective(obj_el))
        return intent

    def _parse_objective(self, el: ET.Element) -> CCLObjective:
        obj = CCLObjective(
            objective_id=el.get("id", ""),
            description=self._text(el, "description"),
            logic=el.get("logic", "AND"),
        )
        for con_el in self._findall(el, "constraint"):
            obj.constraints.append(self._parse_constraint(con_el))
        return obj

    def _parse_constraint(self, el: ET.Element) -> CCLConstraint:
        constraint = CCLConstraint(
            constraint_id=el.get("id", ""),
            constraint_type=el.get("type", "METRIC"),
            description=self._text(el, "description"),
        )
        # Measure
        measure_el = self._find(el, "measure")
        if measure_el is not None:
            constraint.measure = CCLMeasure(
                name=measure_el.get("name", ""),
                unit=self._text(measure_el, "unit"),
                data_type=self._text(measure_el, "data-type") or "FLOAT",
                aggregation=self._text(measure_el, "aggregation") or "MEAN",
            )
        # Threshold
        thr_el = self._find(el, "threshold")
        if thr_el is not None:
            value_text = self._text(thr_el, "value")
            constraint.threshold = CCLThreshold(
                operator=self._text(thr_el, "operator"),
                value=float(value_text) if value_text else 0.0,
                unit=self._text(thr_el, "unit"),
                tolerance=float(self._text(thr_el, "tolerance") or "0"),
                window=self._text(thr_el, "window") or None,
                min_samples=int(self._text(thr_el, "min-samples") or "100"),
            )
        # Evidence requirement
        evr_el = self._find(el, "evidence-requirement")
        if evr_el is not None:
            constraint.evidence_requirement = self._parse_evidence_req(evr_el)
        # Validation condition
        vc_el = self._find(el, "validation-condition")
        if vc_el is not None:
            constraint.validation_condition = CCLValidationCondition(
                condition_type=vc_el.get("type", "DETERMINISTIC"),
                predicate=self._text(vc_el, "predicate"),
            )
        return constraint

    def _parse_evidence_req(self, el: ET.Element) -> CCLEvidenceRequirement:
        evr = CCLEvidenceRequirement(
            requirement_id=el.get("id", ""),
            evidence_type=el.get("evidence-type", "METRIC"),
            freshness=el.get("freshness", "PT24H"),
        )
        for ps_el in self._findall(el, "probe-strategy"):
            evr.probe_strategies.append(CCLProbeStrategy(
                strategy_id=ps_el.get("id", ""),
                probe_type=ps_el.get("probe-type", "LOG_SCAN"),
                method=self._text(ps_el, "method"),
                output_format=self._text(ps_el, "output-format"),
                target_system_ref=self._get_ref(ps_el, "target-system-ref"),
            ))
        return evr

    def _parse_target_system(self, el: ET.Element) -> CCLTargetSystem:
        return CCLTargetSystem(
            system_id=el.get("id", ""),
            system_type=self._text(el, "type"),
            access_method=self._text(el, "access-method"),
            location=self._text(el, "location"),
        )

    def _find(self, parent: ET.Element, tag: str) -> ET.Element | None:
        """Find element with or without namespace."""
        el = parent.find(f"{{{CCL_NS}}}{tag}")
        if el is None:
            el = parent.find(tag)
        if el is None:
            el = parent.find(f"ccl:{tag}", NAMESPACES)
        return el

    def _findall(self, parent: ET.Element, tag: str) -> list[ET.Element]:
        """Find all elements with or without namespace."""
        elements = parent.findall(f"{{{CCL_NS}}}{tag}")
        if not elements:
            elements = parent.findall(tag)
        if not elements:
            elements = parent.findall(f"ccl:{tag}", NAMESPACES)
        return elements

    def _text(self, parent: ET.Element, tag: str) -> str:
        """Get text content of a child element."""
        el = self._find(parent, tag)
        if el is not None and el.text:
            return el.text.strip()
        return ""

    def _get_ref(self, parent: ET.Element, tag: str) -> str:
        """Get ref attribute of a child element."""
        el = self._find(parent, tag)
        if el is not None:
            return el.get("ref", "")
        return ""
