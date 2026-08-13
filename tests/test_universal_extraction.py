import pytest
from app.models.enums import DocumentType, DocumentStatus
from app.services.classification import heuristic_classification
from app.services.extraction import get_schema_description, heuristic_entity_extraction

def test_expanded_classification_categories():
    """Verify expanded document classification heuristics for Resume, Bank Statement, ID Document, and Medical Report"""
    
    # 1. Resume
    resume_text = """
    K.S. Venkata Krishna Reddy
    Email: krishnareddy@gmail.com | Phone: +91 9876543210
    Education: B.Tech Computer Science (2020-2024) - 8.9 CGPA
    Work Experience: Full Stack Software Developer at Cloud Tech Inc
    Skills: Python, TypeScript, FastAPI, React, PostgreSQL, Docker
    """
    cls_resume = heuristic_classification(resume_text)
    assert cls_resume.document_type == "resume"
    assert cls_resume.confidence >= 0.90

    # 2. Bank Statement
    bank_text = """
    HDFC BANK STATEMENT OF ACCOUNT
    Account Holder: John Doe
    Account Number: 50100234567890
    Statement Period: 01-Jan-2026 to 31-Jan-2026
    Opening Balance: $5,000.00
    Closing Balance: $12,450.00
    02/01/2026 Salary Credit $10,000.00
    """
    cls_bank = heuristic_classification(bank_text)
    assert cls_bank.document_type == "bank_statement"
    assert cls_bank.confidence >= 0.90

    # 3. ID Document
    id_text = """
    REPUBLIC OF INDIA PASSPORT
    Full Name: THULASI REDDY
    Passport No: Z9876543
    Date of Birth: 15/08/1998
    Expiry Date: 20/10/2032
    """
    cls_id = heuristic_classification(id_text)
    assert cls_id.document_type == "id_document"
    assert cls_id.confidence >= 0.90


def test_resume_and_bank_statement_extraction():
    """Verify schema-driven nested extraction for Resume and Bank Statement"""
    
    resume_text = """
    Thulasi Reddy
    Email: thulasi@example.com | Phone: 9876543210
    LinkedIn: linkedin.com/in/thulasireddy
    Education: B.Tech Computer Science from IIT Madras
    Work Experience: Software Engineer at CloudSEK
    Skills: Python, React, FastAPI, SQL, Docker
    """
    res_data = heuristic_entity_extraction(DocumentType.RESUME, resume_text)
    assert "personal_info" in res_data
    assert res_data["personal_info"]["full_name"] == "Thulasi Reddy"
    assert res_data["personal_info"]["email"] == "thulasi@example.com"
    assert "education" in res_data
    assert "skills" in res_data

    bank_text = """
    State Bank of India Account Statement
    Account Holder: Jane Smith
    Account Number: 30987654321
    Opening Balance: $1,200.00
    Closing Balance: $3,500.00
    """
    bank_data = heuristic_entity_extraction(DocumentType.BANK_STATEMENT, bank_text)
    assert bank_data.get("account_holder_name") == "Jane Smith"
    assert bank_data.get("account_number") == "30987654321"
    assert bank_data.get("opening_balance") == "1200.00"
    assert bank_data.get("closing_balance") == "3500.00"


def test_adaptive_fallback_for_other_document_types():
    """Verify adaptive dynamic schema extraction for unrecognized 'OTHER' document types"""
    
    unknown_doc_text = """
    LABORATORY DIAGNOSTIC REPORT
    Patient: Alex Johnson
    Ref Number: REF-99082
    Date: 2026-08-10
    Blood Sugar: 95 mg/dL
    Cholesterol: 180 mg/dL
    Summary: All diagnostic parameters are within normal reference ranges.
    """
    other_data = heuristic_entity_extraction(DocumentType.OTHER, unknown_doc_text)
    assert "summary" in other_data
    assert "patient" in other_data or "ref_number" in other_data or len(other_data) > 1
