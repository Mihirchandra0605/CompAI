"""CCL XML Builder — programmatically constructs CCL documents."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree as ET

from .parser import (
    CCLClause,
    CCLConstraint,
    CCLDocument,
    CCLEvidenceRequirement,
    CCLIntent,
    CCLMeasure,
    CCLObjective,
    CCLProbeStrategy,
    CCLRegulation,
    CCLRisk,
    CCLTargetSystem,
    CCLThreshold,
    CCLValidationCondition,
)

CCL_NS = "urn:compliai:ccl:v1"


class CCLBuilder:
    """Builds CCL XML documents programmatically from structured objects."""

    def __init__(self) -> None:
        self._document = CCLDocument()

    def set_metadata(self, version: str = "1.0", generated_by: str = "ccl_builder") -> "CCLBuilder":
        self._document.ccl_version = version
        self._document.generated_by = generated_by
        return self

    def add_target_system(
        self,
        system_id: str,
        system_type: str,
        access_method: str,
        location: str = "",
    ) -> "CCLBuilder":
        self._document.target_systems.append(
            CCLTargetSystem(
                system_id=system_id,
                system_type=system_type,
                access_method=access_method,
                location=location,
            )
        )
        return self

    def set_regulation(
        self,
        regulation_id: str,
        title: str,
        authority: str,
        jurisdiction: str,
        version: str = "",
        effective_date: str = "",
    ) -> "CCLBuilder":
        self._document.regulation = CCLRegulation(
            regulation_id=regulation_id,
            title=title,
            authority=authority,
            jurisdiction=jurisdiction,
            version=version,
            effective_date=effective_date,
        )
        return self

    def add_clause(self, clause: CCLClause) -> "CCLBuilder":
        if self._document.regulation is None:
            raise ValueError("Set regulation before adding clauses")
        self._document.regulation.clauses.append(clause)
        return self

    def build(self) -> CCLDocument:
        """Build and return the CCL document."""
        return self._document

    def to_xml(self) -> str:
        """Serialize the document to XML string."""
        root = ET.Element(f"{{{CCL_NS}}}document")
        root.set("xmlns:ccl", CCL_NS)

        # Metadata
        metadata = ET.SubElement(root, f"{{{CCL_NS}}}metadata")
        ET.SubElement(metadata, f"{{{CCL_NS}}}version").text = self._document.ccl_version
        gen_by = ET.SubElement(metadata, f"{{{CCL_NS}}}generated-by")
        gen_by.set("agent", self._document.generated_by)
        ET.SubElement(metadata, f"{{{CCL_NS}}}schema-version").text = self._document.schema_version

        # Target systems
        if self._document.target_systems:
            ts_container = ET.SubElement(root, f"{{{CCL_NS}}}target-systems")
            for ts in self._document.target_systems:
                ts_el = ET.SubElement(ts_container, f"{{{CCL_NS}}}target-system")
                ts_el.set("id", ts.system_id)
                ET.SubElement(ts_el, f"{{{CCL_NS}}}type").text = ts.system_type
                ET.SubElement(ts_el, f"{{{CCL_NS}}}access-method").text = ts.access_method
                ET.SubElement(ts_el, f"{{{CCL_NS}}}location").text = ts.location

        # Regulation
        if self._document.regulation:
            reg = self._document.regulation
            reg_el = ET.SubElement(root, f"{{{CCL_NS}}}regulation")
            reg_el.set("id", reg.regulation_id)
            ET.SubElement(reg_el, f"{{{CCL_NS}}}title").text = reg.title
            ET.SubElement(reg_el, f"{{{CCL_NS}}}authority").text = reg.authority
            ET.SubElement(reg_el, f"{{{CCL_NS}}}jurisdiction").text = reg.jurisdiction

            for clause in reg.clauses:
                self._build_clause(reg_el, clause)

        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    def _build_clause(self, parent: ET.Element, clause: CCLClause) -> None:
        cl_el = ET.SubElement(parent, f"{{{CCL_NS}}}clause")
        cl_el.set("id", clause.clause_id)
        cl_el.set("section-ref", clause.section_ref)
        ET.SubElement(cl_el, f"{{{CCL_NS}}}text").text = clause.text
        ET.SubElement(cl_el, f"{{{CCL_NS}}}obligation").text = clause.obligation

        if clause.risk:
            risk_el = ET.SubElement(cl_el, f"{{{CCL_NS}}}risk")
            ET.SubElement(risk_el, f"{{{CCL_NS}}}risk-type").text = clause.risk.risk_type
            ET.SubElement(risk_el, f"{{{CCL_NS}}}severity").text = clause.risk.severity

        for intent in clause.intents:
            self._build_intent(cl_el, intent)

    def _build_intent(self, parent: ET.Element, intent: CCLIntent) -> None:
        int_el = ET.SubElement(parent, f"{{{CCL_NS}}}intent")
        int_el.set("id", intent.intent_id)
        ET.SubElement(int_el, f"{{{CCL_NS}}}description").text = intent.description
        if intent.category:
            ET.SubElement(int_el, f"{{{CCL_NS}}}category").text = intent.category

        for obj in intent.objectives:
            self._build_objective(int_el, obj)

    def _build_objective(self, parent: ET.Element, obj: CCLObjective) -> None:
        obj_el = ET.SubElement(parent, f"{{{CCL_NS}}}objective")
        obj_el.set("id", obj.objective_id)
        obj_el.set("logic", obj.logic)
        if obj.description:
            ET.SubElement(obj_el, f"{{{CCL_NS}}}description").text = obj.description

        for con in obj.constraints:
            self._build_constraint(obj_el, con)

    def _build_constraint(self, parent: ET.Element, con: CCLConstraint) -> None:
        con_el = ET.SubElement(parent, f"{{{CCL_NS}}}constraint")
        con_el.set("id", con.constraint_id)
        con_el.set("type", con.constraint_type)

        if con.measure:
            m_el = ET.SubElement(con_el, f"{{{CCL_NS}}}measure")
            m_el.set("name", con.measure.name)
            ET.SubElement(m_el, f"{{{CCL_NS}}}unit").text = con.measure.unit
            ET.SubElement(m_el, f"{{{CCL_NS}}}aggregation").text = con.measure.aggregation

        if con.threshold:
            t_el = ET.SubElement(con_el, f"{{{CCL_NS}}}threshold")
            ET.SubElement(t_el, f"{{{CCL_NS}}}operator").text = con.threshold.operator
            ET.SubElement(t_el, f"{{{CCL_NS}}}value").text = str(con.threshold.value)
            ET.SubElement(t_el, f"{{{CCL_NS}}}unit").text = con.threshold.unit
            if con.threshold.window:
                ET.SubElement(t_el, f"{{{CCL_NS}}}window").text = con.threshold.window
            ET.SubElement(t_el, f"{{{CCL_NS}}}min-samples").text = str(con.threshold.min_samples)

        if con.validation_condition:
            vc_el = ET.SubElement(con_el, f"{{{CCL_NS}}}validation-condition")
            vc_el.set("type", con.validation_condition.condition_type)
            ET.SubElement(vc_el, f"{{{CCL_NS}}}predicate").text = con.validation_condition.predicate
