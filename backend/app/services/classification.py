import json
import re
import logging
from typing import Dict, Any
from app.core.config import settings
from app.models.enums import DocumentType
from app.schemas.classification import ClassificationLLMResult

logger = logging.getLogger(__name__)


CLASSIFICATION_PROMPT_TEMPLATE = """You are an expert Document Classification AI system.
Classify the following raw document text into EXACTLY ONE of these document categories:
- invoice: Billing invoices, tax receipts, commercial invoices, sale memos
- receipt: Retail store receipts, payment vouchers, transaction slips
- contract: Agreements, service contracts, NDAs, legal covenants
- resume: Curriculum vitae, CV, professional resume, candidate profiles
- bank_statement: Bank account statements, credit card statements, transaction summaries
- id_document: Passports, driver licenses, national ID cards, state IDs
- medical_report: Lab test results, doctor prescriptions, clinical summaries, hospital discharges
- purchase_order: Purchase orders, procurement requisitions
- form: Standardized fillable forms, applications, surveys
- report: Financial reports, research papers, executive summaries, status updates
- other: Use ONLY as a genuine last resort if the document matches none of the categories above.

Respond ONLY with valid JSON matching this structure:
{{
  "document_type": "invoice|receipt|contract|resume|bank_statement|id_document|medical_report|purchase_order|form|report|other",
  "confidence": 0.95,
  "reasoning": "Brief explanation of structural indicators found in document text."
}}

Document Raw Text:
\"\"\"
{raw_text}
\"\"\"
"""


def heuristic_classification(raw_text: str) -> ClassificationLLMResult:
    """Intelligent regex/keyword fallback classifier for offline/test environments"""
    text_lower = raw_text.lower() if raw_text else ""

    # 1. Bank Statement (high-precision structural keywords)
    if any(k in text_lower for k in [
        "bank statement", "account statement", "account number", "opening balance", "closing balance",
        "statement period", "account holder", "transaction details"
    ]):
        return ClassificationLLMResult(
            document_type="bank_statement",
            confidence=0.95,
            reasoning="Detected bank statement structural indicators ('account statement', 'opening balance')."
        )

    # 2. Invoice
    elif any(k in text_lower for k in [
        "tax invoice", "sold by", "order summary", "order total", "invoice number",
        "invoice date", "invoice details", "shipping address", "billing address", "gstin"
    ]) or (("invoice" in text_lower or "inv-" in text_lower) and any(k in text_lower for k in ["subtotal", "total amount", "tax", "balance due"])):
        return ClassificationLLMResult(
            document_type="invoice",
            confidence=0.95,
            reasoning="Detected invoice structural indicators ('tax invoice', 'order total', 'sold by', 'subtotal')."
        )

    # 3. Presentation / Slide Deck
    elif any(k in text_lower for k in [
        "presentation", "slide 1", "slide 2", "powerpoint", "keynote", "deck", "speaker notes", "slides"
    ]):
        return ClassificationLLMResult(
            document_type="presentation",
            confidence=0.94,
            reasoning="Detected presentation deck indicators ('presentation', 'slide', 'speaker notes')."
        )

    # 4. ID Document
    elif any(k in text_lower for k in [
        "passport", "driver license", "driver's license", "national id", "identity card",
        "ssn", "social security", "aadhaar", "date of birth", "dob:", "expiry date", "issuing authority"
    ]):
        return ClassificationLLMResult(
            document_type="id_document",
            confidence=0.94,
            reasoning="Detected ID document indicators ('passport', 'driver license', 'date of birth')."
        )

    # 4. Resume / CV
    elif any(k in text_lower for k in [
        "curriculum vitae", "resume", "work experience", "professional experience",
        "academic projects", "technical skills", "career summary",
        "b.tech", "m.tech", "b.e.", "b.s.", "m.s.", "bachelor of", "master of"
    ]) or (re.search(r'\b(curriculum vitae|resume)\b', text_lower)):
        return ClassificationLLMResult(
            document_type="resume",
            confidence=0.96,
            reasoning="Detected resume structural indicators ('education', 'experience', 'skills')."
        )

    # 5. Medical Report
    elif any(k in text_lower for k in [
        "patient name", "diagnosis", "lab report", "blood test", "prescription",
        "clinical summary", "hospital", "doctor:", "physician", "test_name", "reference range"
    ]):
        return ClassificationLLMResult(
            document_type="medical_report",
            confidence=0.93,
            reasoning="Detected medical report indicators ('patient name', 'diagnosis', 'prescription')."
        )

    # 6. Purchase Order
    elif any(k in text_lower for k in ["purchase order", "po-", "po #", "ship to", "vendor name", "buyer"]):
        return ClassificationLLMResult(
            document_type="purchase_order",
            confidence=0.92,
            reasoning="Detected purchase order keywords ('purchase order', 'po #')."
        )

    # 7. Contract / Agreement
    elif any(k in text_lower for k in [
        "agreement", "contract", "parties", "governing law", "expiration date", "effective date",
        "master services", "terms and conditions", "jurisdiction", "payment terms"
    ]):
        return ClassificationLLMResult(
            document_type="contract",
            confidence=0.91,
            reasoning="Detected contract agreement keywords ('agreement', 'governing law')."
        )

    # 8. Receipt
    elif any(k in text_lower for k in ["receipt", "merchant", "visa", "mastercard", "change due", "cashier", "cash receipt", "payment method"]):
        return ClassificationLLMResult(
            document_type="receipt",
            confidence=0.90,
            reasoning="Detected receipt transaction keywords ('receipt', 'merchant')."
        )

    # 9. Report / Study Guide / Document
    elif any(k in text_lower for k in ["report", "executive summary", "author", "key metrics", "quarterly", "financial summary", "study guide", "question bank", "topics"]):
        return ClassificationLLMResult(
            document_type="report",
            confidence=0.88,
            reasoning="Detected report/document structural keywords ('executive summary', 'report', 'study guide')."
        )

    # 10. Form (Require explicit form field markers)
    elif any(k in text_lower for k in ["application form", "fillable form", "form no", "applicant signature", "check one", "signature:"]):
        return ClassificationLLMResult(
            document_type="form",
            confidence=0.85,
            reasoning="Detected explicit fillable form input fields ('application form', 'signature')."
        )

    return ClassificationLLMResult(
        document_type="other",
        confidence=0.50,
        reasoning="Generic fallback: No specific category keywords detected."
    )


def parse_llm_json(response_text: str) -> Dict[str, Any]:
    """Clean markdown code blocks and parse JSON from model response"""
    cleaned = response_text.strip()
    if cleaned.startswith("```json"):
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    elif cleaned.startswith("```"):
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    
    return json.loads(cleaned.strip())


def classify_document_text(raw_text: str, api_key: str = None) -> ClassificationLLMResult:
    """Classify document raw text using Anthropic Claude API or heuristic fallback"""
    key = api_key or settings.ANTHROPIC_API_KEY
    truncated_text = raw_text[:4000] if raw_text else ""

    if not key or key == "your_anthropic_api_key_here":
        logger.info("Anthropic API key not configured. Using heuristic fallback classifier.")
        return heuristic_classification(truncated_text)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(raw_text=truncated_text)

        # Attempt 1: Call Claude API
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )
        res_text = response.content[0].text
        logger.info(f"Raw Claude classification response: {res_text}")
        data = parse_llm_json(res_text)
        return ClassificationLLMResult.model_validate(data)

    except Exception as e:
        logger.error(f"Claude API classification attempt failed: {str(e)}")
        raise RuntimeError(f"Claude API classification failed: {str(e)}") from e
