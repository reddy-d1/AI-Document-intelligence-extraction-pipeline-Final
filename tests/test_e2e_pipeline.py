import os
import io
import sys
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import fitz  # PyMuPDF

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app.main import app
from app.core.database import Base, get_db

from conftest import test_engine, client

def reset_db():
    Base.metadata.create_all(bind=test_engine)


def generate_test_pdf(doc_type_title: str, text_lines: list) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 80), doc_type_title.upper(), fontsize=22)
    y = 120
    for line in text_lines:
        page.insert_text((50, y), line, fontsize=11)
        y += 20
    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


def test_e2e_invoice_lifecycle():
    """Test full E2E lifecycle for Invoice document"""
    reset_db()
    pdf_bytes = generate_test_pdf("INVOICE", [
        "Invoice Number: INV-E2E-1001",
        "Vendor Name: Apex Cloud Solutions",
        "Invoice Date: 2026-08-10",
        "Subtotal: $5,000.00",
        "Tax: $500.00",
        "Total Amount: $5,500.00"
    ])

    res_up = client.post("/api/v1/documents/upload", files={"file": ("invoice_e2e.pdf", pdf_bytes, "application/pdf")})
    assert res_up.status_code == 201
    doc_id = res_up.json()["id"]

    res_proc = client.post(f"/api/v1/documents/{doc_id}/process")
    assert res_proc.status_code == 200
    assert res_proc.json()["status"] in ["validated", "needs_review"]

    res_exp = client.get(f"/api/v1/documents/{doc_id}/export?format=json")
    assert res_exp.status_code == 200
    data = res_exp.json()
    assert data["schema_version"] == "1.0.0"
    assert "extracted_fields" in data


def test_e2e_contract_lifecycle():
    """Test full E2E lifecycle for Contract document"""
    reset_db()
    pdf_bytes = generate_test_pdf("MASTER SERVICES AGREEMENT", [
        "Contract Title: Master Software Licensing Agreement",
        "Effective Date: 2026-01-15",
        "Expiration Date: 2027-01-15",
        "First Party: Alpha Enterprise Tech",
        "Second Party: Beta Global Corp",
        "Contract Value: $120,000.00",
        "Governing Law: State of New York"
    ])

    res_up = client.post("/api/v1/documents/upload", files={"file": ("contract_e2e.pdf", pdf_bytes, "application/pdf")})
    assert res_up.status_code == 201
    doc_id = res_up.json()["id"]

    res_proc = client.post(f"/api/v1/documents/{doc_id}/process")
    assert res_proc.status_code == 200

    res_exp = client.get(f"/api/v1/documents/{doc_id}/export?format=json")
    assert res_exp.status_code == 200
    data = res_exp.json()
    assert data["schema_version"] == "1.0.0"


def test_e2e_purchase_order_lifecycle():
    """Test full E2E lifecycle for Purchase Order document"""
    reset_db()
    pdf_bytes = generate_test_pdf("PURCHASE ORDER", [
        "PO Number: PO-99881",
        "PO Date: 2026-08-01",
        "Vendor: Tech Supplies Inc",
        "Buyer: Enterprise Ops LLC",
        "Total Amount: $4,500.00"
    ])

    res_up = client.post("/api/v1/documents/upload", files={"file": ("po_e2e.pdf", pdf_bytes, "application/pdf")})
    assert res_up.status_code == 201
    doc_id = res_up.json()["id"]

    res_proc = client.post(f"/api/v1/documents/{doc_id}/process")
    assert res_proc.status_code == 200
    assert res_proc.json()["status"] in ["validated", "needs_review", "extracted", "classified"]


if __name__ == "__main__":
    reset_db()
    test_e2e_invoice_lifecycle()
    test_e2e_contract_lifecycle()
    test_e2e_purchase_order_lifecycle()
    print("All End-to-End integration tests executed successfully!")
