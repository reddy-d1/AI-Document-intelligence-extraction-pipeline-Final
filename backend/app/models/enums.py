import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PREPROCESSED = "preprocessed"
    OCR_COMPLETE = "ocr_complete"
    CLASSIFIED = "classified"
    EXTRACTED = "extracted"
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    INVOICE = "invoice"
    CONTRACT = "contract"
    FORM = "form"
    REPORT = "report"
    RECEIPT = "receipt"
    PURCHASE_ORDER = "purchase_order"
    RESUME = "resume"
    BANK_STATEMENT = "bank_statement"
    ID_DOCUMENT = "id_document"
    MEDICAL_REPORT = "medical_report"
    PRESENTATION = "presentation"
    OTHER = "other"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_lower = value.lower()
            for member in cls:
                if member.value == val_lower or member.name.lower() == val_lower:
                    return member
        return cls.OTHER


class DataType(str, enum.Enum):
    STRING = "string"
    DATE = "date"
    NUMBER = "number"
    CURRENCY = "currency"
    JSON = "json"
    BOOLEAN = "boolean"


class ValidationSeverity(str, enum.Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ProcessingStage(str, enum.Enum):
    UPLOAD = "upload"
    PREPROCESSING = "preprocessing"
    OCR = "ocr"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    EXPORT = "export"
