import os
import pytest
from app.models.enums import DocumentType
from app.services.ocr_service import extract_native_docx_text
from app.services.classification import heuristic_classification
from app.services.extraction import heuristic_entity_extraction

def get_sample_docx_path():
    storage = r"c:\Users\reddy\Desktop\Document intelligence extraction pipeline\storage"
    for root, dirs, files in os.walk(storage):
        for f in files:
            if f.endswith(".docx"):
                return os.path.join(root, f)
    return None

def test_native_docx_extraction():
    """Verify native paragraph and markdown table extraction from DOCX file"""
    docx_path = get_sample_docx_path()
    assert docx_path is not None, "Sample DOCX file not found in storage"

    res = extract_native_docx_text(docx_path)
    assert res is not None
    assert res.raw_text is not None
    assert "SAMPLE BANK STATEMENT" in res.raw_text
    assert "ABC National Bank" in res.raw_text
    assert "Renu P." in res.raw_text
    assert "XXXX XXXX 4582" in res.raw_text
    assert "--- Table 1 ---" in res.raw_text
    assert "--- Table 3 ---" in res.raw_text

def test_docx_classification_and_field_extraction():
    """Verify DOCX text classifies as bank_statement and extracts structured account details and transactions"""
    docx_path = get_sample_docx_path()
    res = extract_native_docx_text(docx_path)

    # 1. Classification
    cls = heuristic_classification(res.raw_text)
    assert cls.document_type == "bank_statement"
    assert cls.confidence >= 0.90

    # 2. Entity Extraction
    fields = heuristic_entity_extraction(DocumentType.BANK_STATEMENT, res.raw_text)
    
    assert fields.get("account_holder_name") == "Renu P. (Sample Customer)"
    assert fields.get("account_number") == "XXXX XXXX 4582"
    assert fields.get("bank_name") == "ABC National Bank (Sample)"
    assert fields.get("opening_balance") == "25000.00"
    assert fields.get("closing_balance") == "33750.00"

    txns = fields.get("transactions")
    assert isinstance(txns, list)
    assert len(txns) >= 5

    # Check sample transaction details
    salary_txn = next((t for t in txns if "Salary" in t["description"]), None)
    assert salary_txn is not None
    assert salary_txn["date"] == "02-Aug-2026"
    assert salary_txn["credit"] == 15000.0
    assert salary_txn["balance"] == 40000.0
