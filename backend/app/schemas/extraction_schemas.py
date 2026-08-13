from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from app.models.enums import DataType, DocumentType


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = 1.0
    unit_price: Optional[float] = 0.0
    net_amount: Optional[float] = 0.0
    tax_rate: Optional[str] = None
    tax_type: Optional[str] = None
    tax_amount: Optional[float] = 0.0
    total: Optional[float] = 0.0
    hsn_code: Optional[str] = None


class KeyMetric(BaseModel):
    name: str
    value: str


class KeyValuePair(BaseModel):
    key: str
    value: str


# Extraction schemas per document type
class InvoiceSchema(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    invoice_details: Optional[str] = None
    order_number: Optional[str] = None
    order_date: Optional[str] = None
    due_date: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    vendor_pan: Optional[str] = None
    vendor_gst_number: Optional[str] = None
    vendor_cin: Optional[str] = None
    customer_name: Optional[str] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    state_ut_code: Optional[str] = None
    place_of_supply: Optional[str] = None
    place_of_delivery: Optional[str] = None
    subtotal: Optional[str] = None
    tax: Optional[str] = None
    total_tax_amount: Optional[str] = None
    total_amount: Optional[str] = None
    amount_in_words: Optional[str] = None
    currency: Optional[str] = "INR"
    line_items: List[LineItem] = Field(default_factory=list)



class EducationEntry(BaseModel):
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    institution: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    grade: Optional[str] = None


class WorkExperienceEntry(BaseModel):
    job_title: Optional[str] = None
    company: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class ProjectEntry(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)


class CertificationEntry(BaseModel):
    title: Optional[str] = None
    issuer: Optional[str] = None
    date: Optional[str] = None


class TransactionEntry(BaseModel):
    date: Optional[str] = None
    description: Optional[str] = None
    debit: Optional[float] = 0.0
    credit: Optional[float] = 0.0
    balance: Optional[float] = 0.0


class ResumeSchema(BaseModel):
    personal_info: Dict[str, Any] = Field(default_factory=dict)
    education: List[EducationEntry] = Field(default_factory=list)
    work_experience: List[WorkExperienceEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    certifications: List[CertificationEntry] = Field(default_factory=list)
    skills: Dict[str, List[str]] = Field(default_factory=dict)
    summary: Optional[str] = None


class BankStatementSchema(BaseModel):
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    branch: Optional[str] = None
    statement_period: Optional[str] = None
    opening_balance: Optional[str] = None
    closing_balance: Optional[str] = None
    transactions: List[TransactionEntry] = Field(default_factory=list)


class IDDocumentSchema(BaseModel):
    document_subtype: Optional[str] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    id_number: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    issuing_authority: Optional[str] = None
    address: Optional[str] = None


class MedicalReportSchema(BaseModel):
    patient_name: Optional[str] = None
    patient_dob: Optional[str] = None
    facility_name: Optional[str] = None
    doctor_name: Optional[str] = None
    report_date: Optional[str] = None
    diagnosis: Optional[str] = None
    lab_results: List[Dict[str, Any]] = Field(default_factory=list)
    prescriptions: List[Dict[str, Any]] = Field(default_factory=list)


class ContractSchema(BaseModel):
    parties: List[str] = Field(default_factory=list)
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    contract_value: Optional[str] = None
    payment_terms: Optional[str] = None
    governing_law: Optional[str] = None
    key_clauses: List[str] = Field(default_factory=list)



class FormSchema(BaseModel):
    key_value_pairs: List[KeyValuePair] = Field(default_factory=list)


class ReportSchema(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    summary: Optional[str] = None
    key_metrics: List[KeyMetric] = Field(default_factory=list)


class ReceiptSchema(BaseModel):
    merchant_name: Optional[str] = None
    date: Optional[str] = None
    items: List[LineItem] = Field(default_factory=list)
    tax: Optional[str] = None
    total_amount: Optional[str] = None
    payment_method: Optional[str] = None


class PurchaseOrderSchema(BaseModel):
    po_number: Optional[str] = None
    po_date: Optional[str] = None
    vendor_name: Optional[str] = None
    ship_to_address: Optional[str] = None
    items: List[LineItem] = Field(default_factory=list)
    total_amount: Optional[str] = None


# API response & correction models
class ExtractedFieldResponse(BaseModel):
    id: str
    document_id: str
    field_name: str
    field_value: Optional[str] = None
    confidence_score: float
    data_type: DataType
    bounding_box: Optional[Dict[str, Any]] = None
    is_validated: bool
    validation_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FieldCorrectionRequest(BaseModel):
    field_value: str
    validation_notes: Optional[str] = "Manually corrected by reviewer"


class ExtractionSummaryResponse(BaseModel):
    document_id: str
    document_type: DocumentType
    extracted_fields_count: int
    fields: List[ExtractedFieldResponse]
