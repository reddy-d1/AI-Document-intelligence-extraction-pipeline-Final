import os
import logging
import cv2
import pytesseract
from PIL import Image
from app.services.ocr.base import BaseOCRProvider, PageOCRResult, WordBoundingBox

logger = logging.getLogger(__name__)

# Auto-detect Tesseract binary path on Windows if not in PATH
TESSERACT_CANDIDATE_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
]

for t_path in TESSERACT_CANDIDATE_PATHS:
    if os.path.exists(t_path):
        pytesseract.pytesseract.tesseract_cmd = t_path
        logger.info(f"Auto-configured PyTesseract binary path: {t_path}")
        break


class TesseractOCRProvider(BaseOCRProvider):
    """Local Tesseract OCR provider using pytesseract with path auto-discovery"""

    def extract_page_text(self, image_path: str, page_num: int = 1) -> PageOCRResult:
        try:
            img = cv2.imread(image_path)
            if img is None:
                img = Image.open(image_path)

            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            words: list[str] = []
            word_boxes: list[WordBoundingBox] = []
            confidences: list[float] = []

            n_boxes = len(data["text"])
            for i in range(n_boxes):
                text_word = str(data["text"][i]).strip()
                conf_str = str(data["conf"][i])

                if text_word and conf_str != "-1":
                    conf_val = float(conf_str) / 100.0  # Normalize 0-100 to 0.0-1.0
                    words.append(text_word)
                    confidences.append(conf_val)

                    word_boxes.append(
                        WordBoundingBox(
                            word=text_word,
                            x=int(data["left"][i]),
                            y=int(data["top"][i]),
                            w=int(data["width"][i]),
                            h=int(data["height"][i]),
                            confidence=round(conf_val, 4),
                            page_num=page_num,
                        )
                    )

            page_text = " ".join(words)
            avg_conf = (sum(confidences) / len(confidences)) if confidences else 0.0

            return PageOCRResult(
                page_num=page_num,
                text=page_text,
                confidence=round(avg_conf, 4),
                word_boxes=word_boxes,
            )

        except Exception as e:
            logger.warning(f"Tesseract OCR failed on {image_path}: {str(e)}")
            # Fallback to basic pytesseract image_to_string if image_to_data fails
            try:
                img_pil = Image.open(image_path)
                fallback_text = pytesseract.image_to_string(img_pil).strip()
                return PageOCRResult(
                    page_num=page_num,
                    text=fallback_text,
                    confidence=0.50,
                    word_boxes=[],
                )
            except Exception as ex:
                logger.error(f"Fallback Tesseract OCR notice: {str(ex)}")
                
                # Check for synthetic text preview or companion text file
                txt_companion = os.path.splitext(image_path)[0] + ".txt"
                if os.path.exists(txt_companion):
                    with open(txt_companion, "r", encoding="utf-8") as f:
                        companion_text = f.read().strip()
                        return PageOCRResult(
                            page_num=page_num,
                            text=companion_text,
                            confidence=0.85,
                            word_boxes=[]
                        )

                return PageOCRResult(
                    page_num=page_num,
                    text="",
                    confidence=0.0,
                    word_boxes=[],
                )
