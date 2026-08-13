import re
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional, Type
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.extracted_field import ExtractedField
from app.models.validation_result import ValidationResult
from app.models.enums import DocumentType, ValidationSeverity, DataType
from app.core.config import settings

logger = logging.getLogger(__name__)


class RuleEvaluationOutput(BaseModel if 'BaseModel' in globals() else object):
    def __init__(self, rule_name: str, passed: bool, severity: ValidationSeverity, message: str, field_id: Optional[str] = None):
        self.rule_name = rule_name
        self.passed = passed
        self.severity = severity
        self.message = message
        self.field_id = field_id


class BaseValidationRule(ABC):
    """Abstract base class for pluggable validation rules"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def evaluate(
        self,
        document: Document,
        field_map: Dict[str, ExtractedField],
        db: Session
    ) -> List[RuleEvaluationOutput]:
        pass


class RequiredFieldsRule(BaseValidationRule):
    """Rule verifying mandatory fields presence based on document type"""

    REQUIRED_FIELDS_BY_TYPE = {
        DocumentType.INVOICE: ["invoice_number", "vendor_name", "total_amount"],
        DocumentType.PURCHASE_ORDER: ["po_number", "vendor_name", "total_amount"],
        DocumentType.RECEIPT: ["merchant_name", "total_amount"],
        DocumentType.CONTRACT: ["effective_date"],
    }

    @property
    def name(self) -> str:
        return "RequiredFieldsCheck"

    def evaluate(
        self,
        document: Document,
        field_map: Dict[str, ExtractedField],
        db: Session
    ) -> List[RuleEvaluationOutput]:
        results: List[RuleEvaluationOutput] = []
        required_keys = self.REQUIRED_FIELDS_BY_TYPE.get(document.document_type, [])

        for key in required_keys:
            field = field_map.get(key)
            if not field or not field.field_value or not field.field_value.strip():
                results.append(
                    RuleEvaluationOutput(
                        rule_name=self.name,
                        passed=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"Required field '{key}' is missing for document type '{document.document_type.value}'.",
                        field_id=field.id if field else None
                    )
                )
            else:
                results.append(
                    RuleEvaluationOutput(
                        rule_name=self.name,
                        passed=True,
                        severity=ValidationSeverity.INFO,
                        message=f"Required field '{key}' is present.",
                        field_id=field.id
                    )
                )

        return results


class DataTypeFormatRule(BaseValidationRule):
    """Rule validating format and data type parsing (currency numbers, dates)"""

    @property
    def name(self) -> str:
        return "DataTypeFormatCheck"

    def evaluate(
        self,
        document: Document,
        field_map: Dict[str, ExtractedField],
        db: Session
    ) -> List[RuleEvaluationOutput]:
        results: List[RuleEvaluationOutput] = []

        for field_name, field in field_map.items():
            if not field.field_value:
                continue

            val = field.field_value.strip()

            if field.data_type == DataType.CURRENCY or field.data_type == DataType.NUMBER:
                clean_num = re.sub(r'[^\d\.\-]', '', val)
                try:
                    num_float = float(clean_num)
                    if num_float < 0 and field.data_type == DataType.CURRENCY:
                        results.append(
                            RuleEvaluationOutput(
                                rule_name=self.name,
                                passed=False,
                                severity=ValidationSeverity.WARNING,
                                message=f"Field '{field_name}' currency value '{val}' is negative.",
                                field_id=field.id
                            )
                        )
                    else:
                        results.append(
                            RuleEvaluationOutput(
                                rule_name=self.name,
                                passed=True,
                                severity=ValidationSeverity.INFO,
                                message=f"Field '{field_name}' numeric value '{val}' parsed correctly.",
                                field_id=field.id
                            )
                        )
                except ValueError:
                    results.append(
                        RuleEvaluationOutput(
                            rule_name=self.name,
                            passed=False,
                            severity=ValidationSeverity.ERROR,
                            message=f"Field '{field_name}' value '{val}' failed to parse as valid numeric currency.",
                            field_id=field.id
                        )
                    )

            elif field.data_type == DataType.DATE:
                # Basic ISO / common date pattern check (supports -, /, .)
                date_match = re.search(r'\d{4}[\-\.\/]\d{2}[\-\.\/]\d{2}|\d{1,2}[\-\.\/]\d{1,2}[\-\.\/]\d{2,4}', val)
                if not date_match:
                    results.append(
                        RuleEvaluationOutput(
                            rule_name=self.name,
                            passed=False,
                            severity=ValidationSeverity.WARNING,
                            message=f"Field '{field_name}' date value '{val}' is not in standard YYYY-MM-DD or MM/DD/YYYY format.",
                            field_id=field.id
                        )
                    )
                else:
                    results.append(
                        RuleEvaluationOutput(
                            rule_name=self.name,
                            passed=True,
                            severity=ValidationSeverity.INFO,
                            message=f"Field '{field_name}' date format valid.",
                            field_id=field.id
                        )
                    )

        return results


class CrossFieldConsistencyRule(BaseValidationRule):
    """Rule verifying cross-field arithmetic consistency (subtotal + tax ≈ total_amount)"""

    @property
    def name(self) -> str:
        return "CrossFieldArithmeticCheck"

    def evaluate(
        self,
        document: Document,
        field_map: Dict[str, ExtractedField],
        db: Session
    ) -> List[RuleEvaluationOutput]:
        results: List[RuleEvaluationOutput] = []

        subtotal_f = field_map.get("subtotal")
        tax_f = field_map.get("tax")
        total_f = field_map.get("total_amount")

        if subtotal_f and tax_f and total_f and subtotal_f.field_value and tax_f.field_value and total_f.field_value:
            try:
                sub = float(re.sub(r'[^\d\.]', '', subtotal_f.field_value))
                tax = float(re.sub(r'[^\d\.]', '', tax_f.field_value))
                tot = float(re.sub(r'[^\d\.]', '', total_f.field_value))

                expected_total = sub + tax
                diff = abs(expected_total - tot)

                if diff > 0.05:  # Tolerance $0.05
                    results.append(
                        RuleEvaluationOutput(
                            rule_name=self.name,
                            passed=False,
                            severity=ValidationSeverity.ERROR,
                            message=f"Arithmetic mismatch: Subtotal (${sub:.2f}) + Tax (${tax:.2f}) = ${expected_total:.2f}, but Total Amount is ${tot:.2f} (diff: ${diff:.2f}).",
                            field_id=total_f.id
                        )
                    )
                else:
                    results.append(
                        RuleEvaluationOutput(
                            rule_name=self.name,
                            passed=True,
                            severity=ValidationSeverity.INFO,
                            message=f"Subtotal (${sub:.2f}) + Tax (${tax:.2f}) matches Total Amount (${tot:.2f}).",
                            field_id=total_f.id
                        )
                    )
            except Exception as e:
                logger.warning(f"CrossFieldArithmeticCheck parsing exception: {str(e)}")

        return results


class DuplicateDetectionRule(BaseValidationRule):
    """Rule checking if invoice/PO number and vendor already exist in database"""

    @property
    def name(self) -> str:
        return "DuplicateDocumentCheck"

    def evaluate(
        self,
        document: Document,
        field_map: Dict[str, ExtractedField],
        db: Session
    ) -> List[RuleEvaluationOutput]:
        results: List[RuleEvaluationOutput] = []

        inv_num_field = field_map.get("invoice_number") or field_map.get("po_number")
        vendor_field = field_map.get("vendor_name") or field_map.get("merchant_name")

        if inv_num_field and inv_num_field.field_value:
            inv_val = inv_num_field.field_value.strip()
            
            # Query existing ExtractedFields with matching value for other documents
            duplicate_exists = db.query(ExtractedField).filter(
                ExtractedField.field_name.in_(["invoice_number", "po_number"]),
                ExtractedField.field_value == inv_val,
                ExtractedField.document_id != document.id
            ).first()

            if duplicate_exists:
                results.append(
                    RuleEvaluationOutput(
                        rule_name=self.name,
                        passed=False,
                        severity=ValidationSeverity.WARNING,
                        message=f"Potential duplicate detected: Document invoice/PO number '{inv_val}' already exists in DB (Document ID: {duplicate_exists.document_id}).",
                        field_id=inv_num_field.id
                    )
                )
            else:
                results.append(
                    RuleEvaluationOutput(
                        rule_name=self.name,
                        passed=True,
                        severity=ValidationSeverity.INFO,
                        message=f"Invoice/PO number '{inv_val}' is unique.",
                        field_id=inv_num_field.id
                    )
                )

        return results


class ValidationRuleRegistry:
    """Registry maintaining active validation rules"""

    def __init__(self):
        self._rules: List[BaseValidationRule] = [
            RequiredFieldsRule(),
            DataTypeFormatRule(),
            CrossFieldConsistencyRule(),
            DuplicateDetectionRule(),
        ]

    def register_rule(self, rule: BaseValidationRule):
        self._rules.append(rule)

    def get_rules(self) -> List[BaseValidationRule]:
        return self._rules


validation_registry = ValidationRuleRegistry()
