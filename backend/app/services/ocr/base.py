from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class WordBoundingBox(BaseModel):
    word: str
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    confidence: float = 1.0
    page_num: int = 1


class PageOCRResult(BaseModel):
    page_num: int
    text: str
    confidence: float = 1.0
    word_boxes: List[WordBoundingBox] = Field(default_factory=list)


class DocumentOCRResult(BaseModel):
    raw_text: str
    confidence: float = 1.0
    pages: List[PageOCRResult] = Field(default_factory=list)
    extraction_method: str = "ocr"  # "native_pdf" | "tesseract_ocr" | "cloud_ocr"


class BaseOCRProvider(ABC):
    """Abstract base class for OCR engines"""

    @abstractmethod
    def extract_page_text(self, image_path: str, page_num: int = 1) -> PageOCRResult:
        """Extract text and per-word bounding boxes from a single page image"""
        pass
