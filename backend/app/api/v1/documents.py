import os
import io
import uuid
import math
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query, Response, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.core.database import get_db
from app.core.config import settings
from app.models.document import Document
from app.models.extracted_field import ExtractedField
from app.models.processing_log import ProcessingLog
from app.models.enums import DocumentStatus, DocumentType, ProcessingStage
from app.schemas.document import DocumentCreateResponse, DocumentResponse, DocumentListResponse, DocumentTextResponse
from app.schemas.classification import ClassificationResponse, ClassificationOverrideRequest
from app.schemas.extraction_schemas import ExtractedFieldResponse, FieldCorrectionRequest, ExtractionSummaryResponse
from app.schemas.validation import ValidationResultResponse, ValidationGroupedResponse
from app.schemas.export import StructuredDocumentExport, BatchExportRequest
from app.services.preprocessing import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, preprocess_document
from app.services.ocr_service import process_document_ocr
from app.services.classification_service import run_document_classification, override_document_classification
from app.services.extraction_service import run_document_extraction, correct_extracted_field
from app.services.validation_service import run_document_validation, get_grouped_validation_results
from app.services.export import build_structured_export, export_to_csv, build_batch_zip_export
from app.services.pipeline_orchestrator import run_full_pipeline, run_full_pipeline_background, calculate_pipeline_status
from app.workers.tasks import preprocess_document_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentCreateResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a document (PDF, PNG, JPG, DOCX, TIFF) up to 20MB"""
    filename = file.filename or "file.pdf"
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    contents = await file.read()
    file_size = len(contents)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size / (1024*1024):.2f}MB) exceeds 20MB limit."
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    doc_id = str(uuid.uuid4())
    doc_dir = os.path.join(settings.STORAGE_DIR, doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    file_path = os.path.join(doc_dir, f"original{ext}")
    with open(file_path, "wb") as f:
        f.write(contents)

    now = datetime.now(timezone.utc)
    document = Document(
        id=doc_id,
        filename=filename,
        file_path=file_path,
        file_type=file.content_type or "application/octet-stream",
        upload_date=now,
        status=DocumentStatus.UPLOADED,
        document_type=DocumentType.OTHER,
        page_count=1
    )
    db.add(document)

    upload_log = ProcessingLog(
        document_id=doc_id,
        stage=ProcessingStage.UPLOAD,
        status="completed",
        started_at=now,
        completed_at=now
    )
    db.add(upload_log)
    try:
        db.commit()
        db.refresh(document)
    except Exception as dbe:
        db.rollback()
        logger.error(f"Database commit error during upload for file {filename}: {str(dbe)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist document metadata to database."
        )

    # 1. Queue FastAPI background task for guaranteed auto-processing
    background_tasks.add_task(run_full_pipeline_background, doc_id)

    # 2. Also dispatch to Celery task queue if worker is running
    try:
        preprocess_document_task.delay(doc_id)
    except Exception as e:
        logger.info(f"Celery task queue notice: {str(e)}")

    return DocumentCreateResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        upload_date=document.upload_date,
        status=document.status,
        message="Document uploaded successfully. Processing pipeline queued."
    )



@router.post("/{id}/process", response_model=DocumentResponse)
def process_document_pipeline(id: str, db: Session = Depends(get_db)):
    """Run full pipeline orchestrator (preprocess -> OCR -> classify -> extract -> validate)"""
    try:
        doc = run_full_pipeline(id, db)
        return doc
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.get("/{id}/status")
def get_document_status(id: str, db: Session = Depends(get_db)):
    """Get document status, progress percentage, and current stage info for UI progress bars"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{id}' not found.")
    
    return calculate_pipeline_status(doc)


@router.get("/{id}/stream")
async def stream_document_status(id: str, db: Session = Depends(get_db)):
    """Server-Sent Events (SSE) streaming endpoint for live status updates"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{id}' not found.")

    async def event_generator():
        for _ in range(10):
            db.refresh(doc)
            status_data = calculate_pipeline_status(doc)
            yield f"data: {json.dumps(status_data, default=str)}\n\n"
            if doc.status in [DocumentStatus.VALIDATED, DocumentStatus.NEEDS_REVIEW, DocumentStatus.FAILED]:
                break
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{id}/image")
def get_document_page_image(
    id: str,
    page: int = Query(1, ge=1, description="Page number to view"),
    db: Session = Depends(get_db)
):
    """Retrieve preprocessed PNG image for document page (used by DocumentViewer UI)"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{id}' not found.")

    doc_dir = os.path.join(settings.STORAGE_DIR, id)
    processed_dir = os.path.join(doc_dir, "processed")
    page_img_path = os.path.join(processed_dir, f"page_{page}.png")

    if os.path.exists(page_img_path):
        return FileResponse(page_img_path, media_type="image/png")

    # On-the-fly preprocessing fallback for any document format (PDF, PNG, DOCX, PPTX, etc.)
    if os.path.exists(doc.file_path):
        try:
            prep_res = preprocess_document(id, doc.file_path, settings.STORAGE_DIR)
            new_page_count = prep_res.get("page_count", doc.page_count)
            if new_page_count and new_page_count != doc.page_count:
                doc.page_count = new_page_count
                db.commit()
                db.refresh(doc)
        except Exception as pe:
            logger.warning(f"On-the-fly preprocessing notice for document '{id}': {str(pe)}")

        if os.path.exists(page_img_path):
            return FileResponse(page_img_path, media_type="image/png")

        # Additional fallback if original file is an image
        ext = os.path.splitext(doc.file_path)[1].lower()
        if ext in {".png", ".jpg", ".jpeg", ".tiff", ".tif"}:
            media_type = "image/png" if ext == ".png" else "image/jpeg"
            return FileResponse(doc.file_path, media_type=media_type)
        elif ext == ".pdf":
            try:
                import fitz
                pdf_doc = fitz.open(doc.file_path)
                if 0 <= (page - 1) < len(pdf_doc):
                    pdf_page = pdf_doc.load_page(page - 1)
                    pix = pdf_page.get_pixmap(dpi=150)
                    os.makedirs(processed_dir, exist_ok=True)
                    pix.save(page_img_path)
                    pdf_doc.close()
                    return FileResponse(page_img_path, media_type="image/png")
                pdf_doc.close()
            except Exception as e:
                logger.warning(f"On-the-fly PDF page render error: {str(e)}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Page image {page} not found for document '{id}'."
    )


@router.get("/{id}/file")
def get_original_document_file(id: str, db: Session = Depends(get_db)):
    """Retrieve original uploaded document file stream"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{id}' not found.")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Original file for document '{id}' missing from storage.")

    return FileResponse(doc.file_path, filename=doc.filename, media_type=doc.file_type)


@router.get("/{id}/logs")
def get_document_processing_logs(id: str, db: Session = Depends(get_db)):
    """Retrieve chronological audit trail logs for a document with computed durations"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{id}' not found.")

    logs = db.query(ProcessingLog).filter(ProcessingLog.document_id == id).order_by(ProcessingLog.started_at.asc()).all()

    result = []
    for log in logs:
        duration_ms = None
        if log.started_at and log.completed_at:
            duration_ms = int((log.completed_at - log.started_at).total_seconds() * 1000)

        result.append({
            "id": log.id,
            "stage": log.stage.value,
            "status": log.status,
            "started_at": log.started_at,
            "completed_at": log.completed_at,
            "duration_ms": duration_ms,
            "error_message": log.error_message
        })

    return result


@router.get("/{id}/export")
def export_document(
    id: str,
    format: str = Query("json", description="Export format: 'json' or 'csv'"),
    db: Session = Depends(get_db)
):
    """Export final structured document data in versioned JSON (schema 1.0.0) or CSV format"""
    try:
        if format.lower() == "csv":
            csv_content = export_to_csv(id, db)
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={id}_export.csv"}
            )
        else:
            export_obj = build_structured_export(id, db)
            return export_obj
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.post("/batch-export")
def batch_export_documents(
    payload: BatchExportRequest,
    db: Session = Depends(get_db)
):
    """Batch export multiple documents into a ZIP archive or combined JSON array"""
    doc_ids = payload.document_ids or []
    if not doc_ids:
        docs = db.query(Document.id).limit(50).all()
        doc_ids = [d.id for d in docs]

    if payload.as_zip:
        zip_bytes = build_batch_zip_export(doc_ids, db)
        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=documents_batch_export.zip"}
        )
    else:
        results = []
        for d_id in doc_ids:
            try:
                results.append(build_structured_export(d_id, db))
            except Exception:
                pass
        return results


@router.get("/{id}", response_model=DocumentResponse)
def get_document(id: str, db: Session = Depends(get_db)):
    """Retrieve document metadata and current processing status"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{id}' not found."
        )
    return doc


@router.get("/{id}/text", response_model=DocumentTextResponse)
def get_document_raw_text(id: str, db: Session = Depends(get_db)):
    """Retrieve raw extracted text for a document"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{id}' not found."
        )
    return DocumentTextResponse(
        document_id=doc.id,
        filename=doc.filename,
        status=doc.status,
        raw_text=doc.raw_text,
        page_count=doc.page_count
    )


@router.post("/{id}/ocr", response_model=DocumentTextResponse)
def trigger_document_ocr(id: str, db: Session = Depends(get_db)):
    """Manually trigger or re-run OCR extraction for a document"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{id}' not found."
        )

    ocr_res = process_document_ocr(doc.id, doc.file_path, settings.STORAGE_DIR)
    doc.raw_text = ocr_res.raw_text
    
    if ocr_res.confidence < 0.60:
        doc.status = DocumentStatus.NEEDS_REVIEW
    else:
        doc.status = DocumentStatus.OCR_COMPLETE

    db.commit()
    db.refresh(doc)

    return DocumentTextResponse(
        document_id=doc.id,
        filename=doc.filename,
        status=doc.status,
        raw_text=doc.raw_text,
        page_count=doc.page_count
    )


@router.post("/{id}/classify", response_model=ClassificationResponse)
def trigger_document_classification(id: str, db: Session = Depends(get_db)):
    """Manually trigger document classification"""
    try:
        cls_obj = run_document_classification(id, db)
        doc = db.query(Document).filter(Document.id == id).first()
        return ClassificationResponse(
            id=cls_obj.id,
            document_id=cls_obj.document_id,
            predicted_type=cls_obj.predicted_type,
            confidence_score=cls_obj.confidence_score,
            model_used=cls_obj.model_used,
            classified_at=cls_obj.classified_at,
            status=doc.status
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.post("/{id}/classification/override", response_model=ClassificationResponse)
def override_classification(
    id: str,
    payload: ClassificationOverrideRequest,
    db: Session = Depends(get_db)
):
    """Manually override document classification type"""
    try:
        cls_obj = override_document_classification(id, payload.override_type, payload.reasoning, db)
        doc = db.query(Document).filter(Document.id == id).first()
        return ClassificationResponse(
            id=cls_obj.id,
            document_id=cls_obj.document_id,
            predicted_type=cls_obj.predicted_type,
            confidence_score=cls_obj.confidence_score,
            model_used=cls_obj.model_used,
            classified_at=cls_obj.classified_at,
            status=doc.status
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.post("/{id}/extract", response_model=ExtractionSummaryResponse)
def trigger_document_extraction(id: str, db: Session = Depends(get_db)):
    """Manually trigger key-value and entity extraction"""
    try:
        fields = run_document_extraction(id, db)
        doc = db.query(Document).filter(Document.id == id).first()
        return ExtractionSummaryResponse(
            document_id=doc.id,
            document_type=doc.document_type,
            extracted_fields_count=len(fields),
            fields=fields
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.get("/{id}/fields", response_model=List[ExtractedFieldResponse])
def get_document_extracted_fields(id: str, db: Session = Depends(get_db)):
    """Retrieve all extracted fields for a document"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID '{id}' not found.")

    fields = db.query(ExtractedField).filter(ExtractedField.document_id == id).all()
    return fields


@router.patch("/{id}/fields/{field_id}", response_model=ExtractedFieldResponse)
def update_extracted_field(
    id: str,
    field_id: str,
    payload: FieldCorrectionRequest,
    db: Session = Depends(get_db)
):
    """Human-in-the-loop (HITL) field correction endpoint"""
    try:
        updated_field = correct_extracted_field(id, field_id, payload.field_value, payload.validation_notes, db)
        return updated_field
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.post("/{id}/validate", response_model=ValidationGroupedResponse)
def trigger_document_validation(id: str, db: Session = Depends(get_db)):
    """Trigger complete rule validation for a document"""
    try:
        run_document_validation(id, db)
        grouped = get_grouped_validation_results(id, db)
        return grouped
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.get("/{id}/validation", response_model=ValidationGroupedResponse)
def get_document_validation_results(id: str, db: Session = Depends(get_db)):
    """Retrieve validation results grouped by severity (errors, warnings, info)"""
    try:
        grouped = get_grouped_validation_results(id, db)
        return grouped
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.get("", response_model=DocumentListResponse)
def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    q: Optional[str] = Query(None, description="Search query string across filename, raw text, and extracted fields"),
    status: Optional[DocumentStatus] = Query(None, description="Filter by status"),
    document_type: Optional[DocumentType] = Query(None, description="Filter by document type"),
    start_date: Optional[datetime] = Query(None, description="Filter upload date from"),
    end_date: Optional[datetime] = Query(None, description="Filter upload date to"),
    db: Session = Depends(get_db)
):
    """List documents with full-text search, pagination, and multi-param filtering options"""
    query = db.query(Document)

    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        # Subquery for extracted field text match
        matching_field_doc_ids = db.query(ExtractedField.document_id).filter(
            ExtractedField.field_value.ilike(search_pattern)
        ).subquery()

        query = query.filter(
            or_(
                Document.filename.ilike(search_pattern),
                Document.raw_text.ilike(search_pattern),
                Document.id.in_(matching_field_doc_ids)
            )
        )

    if status:
        query = query.filter(Document.status == status)
    if document_type:
        query = query.filter(Document.document_type == document_type)
    if start_date:
        query = query.filter(Document.upload_date >= start_date)
    if end_date:
        query = query.filter(Document.upload_date <= end_date)

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(desc(Document.upload_date)).offset(offset).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
