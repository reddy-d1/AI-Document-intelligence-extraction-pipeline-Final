import os
import time
import sys
import numpy as np
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import fitz

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app.core.database import Base
from app.services.preprocessing import preprocess_document
from app.services.ocr_service import process_document_ocr
from app.services.classification_service import run_document_classification
from app.services.extraction_service import run_document_extraction
from app.services.validation_service import run_document_validation
from app.models.document import Document
from app.models.enums import DocumentStatus, DocumentType
import uuid

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def generate_multi_page_pdf(page_count: int) -> tuple[str, str]:
    storage_dir = os.path.join(os.path.dirname(__file__), "../storage")
    os.makedirs(storage_dir, exist_ok=True)
    doc_id = str(uuid.uuid4())
    doc_dir = os.path.join(storage_dir, doc_id)
    os.makedirs(doc_dir, exist_ok=True)
    pdf_path = os.path.join(doc_dir, "original.pdf")

    doc = fitz.open()
    for i in range(page_count):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 80), f"INVOICE PAGE {i+1}", fontsize=20)
        page.insert_text((50, 120), f"Invoice Number: INV-LATENCY-{doc_id[:6]}", fontsize=12)
        page.insert_text((50, 140), "Subtotal: $1,000.00", fontsize=12)
        page.insert_text((50, 160), "Tax: $100.00", fontsize=12)
        page.insert_text((50, 180), "Total Amount: $1,100.00", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    return doc_id, pdf_path


def benchmark_stage_latency():
    Base.metadata.create_all(bind=engine)
    db = TestingSession()

    test_runs = [1, 3, 5]
    latencies = {
        "preprocessing": [],
        "ocr": [],
        "classification": [],
        "extraction": [],
        "validation": [],
        "total_e2e": []
    }

    print("=" * 60)
    print("      STAGE LATENCY BENCHMARKING REPORT (P50 / P90 / P99)      ")
    print("=" * 60)

    for pages in test_runs:
        doc_id, pdf_path = generate_multi_page_pdf(pages)
        doc = Document(
            id=doc_id,
            filename=f"latency_{pages}pg.pdf",
            file_path=pdf_path,
            file_type="application/pdf",
            upload_date=datetime.now(timezone.utc),
            status=DocumentStatus.UPLOADED,
            document_type=DocumentType.OTHER,
            page_count=pages
        )
        db.add(doc)
        db.commit()

        # 1. Preprocessing
        t0 = time.perf_counter()
        preprocess_document(doc_id, pdf_path)
        t_prep = (time.perf_counter() - t0) * 1000
        latencies["preprocessing"].append(t_prep)

        # 2. OCR
        t0 = time.perf_counter()
        process_document_ocr(doc_id, pdf_path)
        t_ocr = (time.perf_counter() - t0) * 1000
        latencies["ocr"].append(t_ocr)

        # 3. Classification
        t0 = time.perf_counter()
        run_document_classification(doc_id, db)
        t_cls = (time.perf_counter() - t0) * 1000
        latencies["classification"].append(t_cls)

        # 4. Extraction
        t0 = time.perf_counter()
        run_document_extraction(doc_id, db)
        t_ext = (time.perf_counter() - t0) * 1000
        latencies["extraction"].append(t_ext)

        # 5. Validation
        t0 = time.perf_counter()
        run_document_validation(doc_id, db)
        t_val = (time.perf_counter() - t0) * 1000
        latencies["validation"].append(t_val)

        total_e2e = t_prep + t_ocr + t_cls + t_ext + t_val
        latencies["total_e2e"].append(total_e2e)

        print(f"[{pages} Page Doc] E2E: {total_e2e:.1f}ms | Prep: {t_prep:.1f}ms | OCR: {t_ocr:.1f}ms | Classify: {t_cls:.1f}ms | Extract: {t_ext:.1f}ms | Validate: {t_val:.1f}ms")

    print("-" * 60)
    print(f"{'Stage':<18} | {'p50 (ms)':<10} | {'p90 (ms)':<10} | {'p99 (ms)':<10}")
    print("-" * 60)
    for stage, arr in latencies.items():
        p50 = float(np.percentile(arr, 50))
        p90 = float(np.percentile(arr, 90))
        p99 = float(np.percentile(arr, 99))
        print(f"{stage:<18} | {p50:<10.1f} | {p90:<10.1f} | {p99:<10.1f}")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    benchmark_stage_latency()
