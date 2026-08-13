import os
import io
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import fitz

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app.core.database import Base
from app.services.pipeline_orchestrator import run_full_pipeline
from app.services.export import build_structured_export
from app.models.document import Document
from app.models.enums import DocumentStatus, DocumentType
from datetime import datetime, timezone
import uuid

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

GROUND_TRUTH_DATASET = [
    {
        "type": "invoice",
        "title": "INVOICE",
        "text": [
            "Invoice Number: INV-2026-BENCH",
            "Vendor Name: Acme Cloud Inc",
            "Invoice Date: 2026-08-11",
            "Subtotal: $1,000.00",
            "Tax: $100.00",
            "Total Amount: $1,100.00"
        ],
        "expected_fields": {
            "invoice_number": "INV-2026-BENCH",
            "vendor_name": "Acme Cloud Inc",
            "subtotal": "1000.00",
            "tax": "100.00",
            "total_amount": "1100.00"
        }
    },
    {
        "type": "contract",
        "title": "SERVICE AGREEMENT",
        "text": [
            "Contract Title: Enterprise Cloud SLA",
            "Effective Date: 2026-05-01",
            "First Party: Omega Corp",
            "Second Party: Zenith Labs"
        ],
        "expected_fields": {
            "contract_title": "Enterprise Cloud SLA",
            "effective_date": "2026-05-01",
            "first_party": "Omega Corp",
            "second_party": "Zenith Labs"
        }
    }
]


def generate_pdf_buffer(title: str, lines: list) -> str:
    storage_dir = os.path.join(os.path.dirname(__file__), "../storage")
    os.makedirs(storage_dir, exist_ok=True)
    doc_id = str(uuid.uuid4())
    doc_dir = os.path.join(storage_dir, doc_id)
    os.makedirs(doc_dir, exist_ok=True)
    pdf_path = os.path.join(doc_dir, "original.pdf")

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 80), title, fontsize=22)
    y = 120
    for line in lines:
        page.insert_text((50, y), line, fontsize=11)
        y += 20
    doc.save(pdf_path)
    doc.close()
    return doc_id, pdf_path


def run_accuracy_benchmark():
    Base.metadata.create_all(bind=engine)
    db = TestingSession()

    tp = 0
    fp = 0
    fn = 0

    print("=" * 60)
    print("      ACCURACY BENCHMARKING REPORT (PRECISION / RECALL / F1)      ")
    print("=" * 60)

    for item in GROUND_TRUTH_DATASET:
        doc_id, pdf_path = generate_pdf_buffer(item["title"], item["text"])
        doc = Document(
            id=doc_id,
            filename=f"{item['type']}_bench.pdf",
            file_path=pdf_path,
            file_type="application/pdf",
            upload_date=datetime.now(timezone.utc),
            status=DocumentStatus.UPLOADED,
            document_type=DocumentType.OTHER,
            page_count=1
        )
        db.add(doc)
        db.commit()

        run_full_pipeline(doc_id, db)
        export_data = build_structured_export(doc_id, db)
        extracted = export_data.extracted_fields

        exp_fields = item["expected_fields"]
        for key, exp_val in exp_fields.items():
            if key in extracted and extracted[key]["value"] is not None:
                actual_val = str(extracted[key]["value"]).replace(",", "").replace("$", "").strip()
                target_val = str(exp_val).replace(",", "").replace("$", "").strip()
                if actual_val.lower() == target_val.lower():
                    tp += 1
                else:
                    fp += 1
            else:
                fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0

    print(f"Total True Positives (TP):  {tp}")
    print(f"Total False Positives (FP): {fp}")
    print(f"Total False Negatives (FN): {fn}")
    print(f"Field-Level Precision:     {precision * 100:.2f}%")
    print(f"Field-Level Recall:        {recall * 100:.2f}%")
    print(f"Field-Level F1-Score:      {f1 * 100:.2f}%")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    run_accuracy_benchmark()
