"""CCL Validator — multi-level validation of CCL documents."""

from __future__ import annotations

import logging
from enum import Enum

from pydantic import BaseModel, Field

from .parser import CCLDocument

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    SCHEMA = "schema"
    REFERENTIAL = "referential"
    SEMANTIC = "semantic"
    EXECUTION = "execution"


class ValidationIssue(BaseModel):
    """A single validation issue found in a CCL document."""

    level: ValidationLevel
    rule_id: str
    message: str
    element_id: str = ""
    severity: str = "error"  # error, warning


class CCLValidationResult(BaseModel):
    """Result of CCL document validation."""

    is_valid: bool = True
    issues: list[ValidationIssue] = Field(default_factory=list)
    level_results: dict[str, bool] = Field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


class CCLValidator:
    """
    Multi-level CCL validator.

    Validates:
    1. Schema (structural) — required elements present
    2. Referential (integrity) — cross-references valid
    3. Semantic (meaning) — logical consistency
    4. Execution (completeness) — ready for probe execution
    """

    def validate(
        self, document: CCLDocument, levels: list[ValidationLevel] | None = None
    ) -> CCLValidationResult:
        """Validate a CCL document at specified levels."""
        if levels is None:
            levels = [ValidationLevel.SCHEMA, ValidationLevel.REFERENTIAL, ValidationLevel.SEMANTIC]

        result = CCLValidationResult()

        if ValidationLevel.SCHEMA in levels:
            schema_valid = self._validate_schema(document, result)
            result.level_results["schema"] = schema_valid

        if ValidationLevel.REFERENTIAL in levels:
            ref_valid = self._validate_referential(document, result)
            result.level_results["referential"] = ref_valid

        if ValidationLevel.SEMANTIC in levels:
            sem_valid = self._validate_semantic(document, result)
            result.level_results["semantic"] = sem_valid

        if ValidationLevel.EXECUTION in levels:
            exec_valid = self._validate_execution(document, result)
            result.level_results["execution"] = exec_valid

        result.is_valid = result.error_count == 0
        return result

    def _validate_schema(self, doc: CCLDocument, result: CCLValidationResult) -> bool:
        """SV rules: structural validation."""
        valid = True

        # SV-001: Document has a regulation
        if doc.regulation is None:
            result.issues.append(ValidationIssue(
                level=ValidationLevel.SCHEMA,
                rule_id="SV-001",
                message="Document must contain exactly one regulation",
            ))
            valid = False
            return valid

        reg = doc.regulation

        # SV-002: Regulation has ID
        if not reg.regulation_id:
            result.issues.append(ValidationIssue(
                level=ValidationLevel.SCHEMA,
                rule_id="SV-002",
                message="Regulation must have an id attribute",
            ))
            valid = False

        # Check clauses
        for clause in reg.clauses:
            # SV-003: Clause has section_ref and obligation
            if not clause.section_ref:
                result.issues.append(ValidationIssue(
                    level=ValidationLevel.SCHEMA,
                    rule_id="SV-003",
                    message=f"Clause {clause.clause_id} missing section-ref",
                    element_id=clause.clause_id,
                ))
                valid = False

            if not clause.obligation:
                result.issues.append(ValidationIssue(
                    level=ValidationLevel.SCHEMA,
                    rule_id="SV-003",
                    message=f"Clause {clause.clause_id} missing obligation",
                    element_id=clause.clause_id,
                ))
                valid = False

            for intent in clause.intents:
                for obj in intent.objectives:
                    # SV-006: Objective has logic
                    if obj.logic not in ("AND", "OR"):
                        result.issues.append(ValidationIssue(
                            level=ValidationLevel.SCHEMA,
                            rule_id="SV-006",
                            message=f"Objective {obj.objective_id} has invalid logic: {obj.logic}",
                            element_id=obj.objective_id,
                        ))
                        valid = False

                    for con in obj.constraints:
                        # SV-004: Constraint has type
                        if not con.constraint_type:
                            result.issues.append(ValidationIssue(
                                level=ValidationLevel.SCHEMA,
                                rule_id="SV-004",
                                message=f"Constraint {con.constraint_id} missing type",
                                element_id=con.constraint_id,
                            ))
                            valid = False

                        # SV-005: Threshold has operator, value, unit
                        if con.threshold:
                            if not con.threshold.operator:
                                result.issues.append(ValidationIssue(
                                    level=ValidationLevel.SCHEMA,
                                    rule_id="SV-005",
                                    message=f"Constraint {con.constraint_id} threshold missing operator",
                                    element_id=con.constraint_id,
                                ))
                                valid = False

        return valid

    def _validate_referential(self, doc: CCLDocument, result: CCLValidationResult) -> bool:
        """RV rules: referential integrity."""
        valid = True
        target_ids = {ts.system_id for ts in doc.target_systems}
        all_ids: set[str] = set()

        if doc.regulation:
            for clause in doc.regulation.clauses:
                # RV-003: No duplicate IDs
                if clause.clause_id in all_ids:
                    result.issues.append(ValidationIssue(
                        level=ValidationLevel.REFERENTIAL,
                        rule_id="RV-003",
                        message=f"Duplicate ID: {clause.clause_id}",
                        element_id=clause.clause_id,
                    ))
                    valid = False
                all_ids.add(clause.clause_id)

                for intent in clause.intents:
                    all_ids.add(intent.intent_id)
                    for obj in intent.objectives:
                        all_ids.add(obj.objective_id)
                        for con in obj.constraints:
                            all_ids.add(con.constraint_id)
                            # RV-001: target-system-ref points to existing target
                            if con.evidence_requirement:
                                for ps in con.evidence_requirement.probe_strategies:
                                    if ps.target_system_ref and ps.target_system_ref not in target_ids:
                                        result.issues.append(ValidationIssue(
                                            level=ValidationLevel.REFERENTIAL,
                                            rule_id="RV-001",
                                            message=(
                                                f"Probe strategy {ps.strategy_id} references "
                                                f"non-existent target system: {ps.target_system_ref}"
                                            ),
                                            element_id=ps.strategy_id,
                                        ))
                                        valid = False

        return valid

    def _validate_semantic(self, doc: CCLDocument, result: CCLValidationResult) -> bool:
        """SEM rules: semantic consistency."""
        valid = True

        if doc.regulation:
            for clause in doc.regulation.clauses:
                # SEM-001: MANDATORY clause needs intents
                if clause.obligation == "MANDATORY" and not clause.intents:
                    result.issues.append(ValidationIssue(
                        level=ValidationLevel.SEMANTIC,
                        rule_id="SEM-001",
                        message=f"Mandatory clause {clause.clause_id} has no intents",
                        element_id=clause.clause_id,
                    ))
                    valid = False

                for intent in clause.intents:
                    for obj in intent.objectives:
                        # SEM-002: Objective has constraints
                        if not obj.constraints:
                            result.issues.append(ValidationIssue(
                                level=ValidationLevel.SEMANTIC,
                                rule_id="SEM-002",
                                message=f"Objective {obj.objective_id} has no constraints",
                                element_id=obj.objective_id,
                            ))
                            valid = False

                        for con in obj.constraints:
                            # SEM-003: Constraint has evidence requirement
                            if not con.evidence_requirement:
                                result.issues.append(ValidationIssue(
                                    level=ValidationLevel.SEMANTIC,
                                    rule_id="SEM-003",
                                    message=f"Constraint {con.constraint_id} has no evidence requirement",
                                    element_id=con.constraint_id,
                                    severity="warning",
                                ))

                            # SEM-005: Unit consistency
                            if con.measure and con.threshold:
                                if con.measure.unit and con.threshold.unit:
                                    if con.measure.unit != con.threshold.unit:
                                        result.issues.append(ValidationIssue(
                                            level=ValidationLevel.SEMANTIC,
                                            rule_id="SEM-005",
                                            message=(
                                                f"Constraint {con.constraint_id}: "
                                                f"measure unit ({con.measure.unit}) != "
                                                f"threshold unit ({con.threshold.unit})"
                                            ),
                                            element_id=con.constraint_id,
                                        ))
                                        valid = False

                            # SEM-009: min_samples positive
                            if con.threshold and con.threshold.min_samples <= 0:
                                result.issues.append(ValidationIssue(
                                    level=ValidationLevel.SEMANTIC,
                                    rule_id="SEM-009",
                                    message=f"Constraint {con.constraint_id}: min_samples must be positive",
                                    element_id=con.constraint_id,
                                ))
                                valid = False

        return valid

    def _validate_execution(self, doc: CCLDocument, result: CCLValidationResult) -> bool:
        """EV rules: execution readiness."""
        valid = True

        if doc.regulation:
            for clause in doc.regulation.clauses:
                for intent in clause.intents:
                    for obj in intent.objectives:
                        for con in obj.constraints:
                            # EV-003: DETERMINISTIC has parseable predicate
                            if con.validation_condition:
                                if con.validation_condition.condition_type == "DETERMINISTIC":
                                    if not con.validation_condition.predicate:
                                        result.issues.append(ValidationIssue(
                                            level=ValidationLevel.EXECUTION,
                                            rule_id="EV-003",
                                            message=(
                                                f"Constraint {con.constraint_id}: "
                                                "DETERMINISTIC validation condition has no predicate"
                                            ),
                                            element_id=con.constraint_id,
                                        ))
                                        valid = False

        return valid
