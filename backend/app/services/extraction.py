import json
import re
import logging
from typing import Dict, Any, List
from app.core.config import settings
from app.models.enums import DocumentType, DataType
from app.services.classification import parse_llm_json

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT_TEMPLATE = """You are an enterprise-grade AI Universal Document Entity Extractor.
Extract ALL structured fields present in the document raw text based on the document category: '{document_type}'.

Goal: Comprehensively capture every meaningful field present in the source document into well-structured, nested JSON matching the schema below. Group repeating elements (like education entries, transaction rows, line items, or test results) into arrays of objects.

Target Schema Fields to Extract:
{schema_description}

Critical Extraction Rules:
1. Return strictly valid JSON containing all available fields. Group nested data into proper JSON objects and arrays. Use null only for fields genuinely absent in the source document.
2. Vendor / Seller Name (Invoices): Look explicitly for the business name following 'Sold By:' or 'Regd Office:'. Do NOT extract arbitrary text like 'Business eligible offers'.
3. Resumes: Extract candidate name, email, phone, links, education array, work experience array, projects array, certifications array, and categorized skills.
4. Bank Statements: Extract account holder, account number, bank name, statement period, opening balance, closing balance, and transaction array.
5. Dynamic Adaptive Mode (Unrecognized / 'other' types): Analyze content and structure, then extract ALL meaningful information into a clear JSON object with descriptive key names and arrays for repeating records.
6. Include a confidence score (0.0 to 1.0) for each top-level field or section inside a top-level '_field_confidence' map.

Document Raw Text:
\"\"\"
{raw_text}
\"\"\"
"""


def get_schema_description(document_type: DocumentType) -> str:
    """Return explicit JSON schema field guidance for LLM prompts across all document types"""
    if document_type in [DocumentType.INVOICE, DocumentType.RECEIPT, DocumentType.PURCHASE_ORDER]:
        return json.dumps({
            "vendor_name": "Legal name of selling/merchant entity (found after 'Sold By:' or 'Regd Office:')",
            "vendor_address": "Complete registered/office address of vendor",
            "vendor_pan": "10-character Income Tax Permanent Account Number (PAN) e.g. AAICA3918J",
            "vendor_gst_number": "15-character GSTIN number e.g. 29AAICA3918J1ZE",
            "vendor_cin": "21-character Corporate Identification Number (CIN)",
            "customer_name": "Name of purchaser / billed customer",
            "billing_address": "Full billing address of purchaser",
            "shipping_address": "Full shipping address of purchaser",
            "state_ut_code": "State / UT Code e.g. 37",
            "place_of_supply": "Place of supply state / region",
            "place_of_delivery": "Place of delivery state / region",
            "order_number": "Order reference / PO number e.g. 405-5353195-7052351",
            "order_date": "Order date e.g. 13.06.2026",
            "invoice_number": "Tax invoice number e.g. POD-27-79199340 or IN-6076",
            "invoice_details": "Invoice details reference string e.g. DL-1044-2627",
            "invoice_date": "Invoice issue date e.g. 13.06.2026",
            "due_date": "Payment due date if specified",
            "subtotal": "Net subtotal amount before taxes",
            "tax": "Total tax / IGST / CGST / SGST amount",
            "total_tax_amount": "Total tax amount",
            "total_amount": "Grand total invoice amount",
            "amount_in_words": "Total invoice amount written in words e.g. Nine Point Eight only",
            "currency": "Currency code e.g. INR or USD",
            "line_items": [
                {
                    "description": "Item or service description",
                    "unit_price": 0.0,
                    "quantity": 1.0,
                    "net_amount": 0.0,
                    "tax_rate": "18%",
                    "tax_type": "IGST",
                    "tax_amount": 0.0,
                    "total": 0.0
                }
            ]
        }, indent=2)

    elif document_type == DocumentType.RESUME:
        return json.dumps({
            "personal_info": {
                "full_name": "Candidate full name",
                "email": "Email address",
                "phone": "Phone number",
                "location": "City, State, Country",
                "linkedin": "LinkedIn profile URL",
                "github": "GitHub portfolio URL"
            },
            "summary": "Executive candidate summary / objective",
            "education": [
                {
                    "degree": "Degree e.g. B.Tech Computer Science",
                    "field_of_study": "Specialization e.g. Computer Science",
                    "institution": "University / College name",
                    "start_year": "Start year",
                    "end_year": "End year / graduation year",
                    "grade": "CGPA / Percentage"
                }
            ],
            "work_experience": [
                {
                    "job_title": "Position / Role title",
                    "company": "Company name",
                    "start_date": "Start date",
                    "end_date": "End date or Present",
                    "description": "Key responsibilities and achievements"
                }
            ],
            "projects": [
                {
                    "title": "Project title",
                    "date": "Project date / timeline",
                    "description": "Project overview and outcomes",
                    "technologies": ["List of tools / technologies used"]
                }
            ],
            "certifications": [
                {
                    "title": "Certification name",
                    "issuer": "Issuing organization",
                    "date": "Issue date"
                }
            ],
            "skills": {
                "programming_languages": ["Python", "TypeScript"],
                "frameworks_and_libraries": ["FastAPI", "React", "Node.js"],
                "tools_and_databases": ["PostgreSQL", "Redis", "Docker", "Git"]
            }
        }, indent=2)

    elif document_type == DocumentType.BANK_STATEMENT:
        return json.dumps({
            "account_holder_name": "Full legal name of account holder",
            "account_number": "Bank account number",
            "bank_name": "Name of issuing bank",
            "branch": "Branch location / IFSC code",
            "statement_period": "Statement start and end dates e.g. 01-Jan-2026 to 31-Jan-2026",
            "opening_balance": "Starting account balance",
            "closing_balance": "Ending account balance",
            "transactions": [
                {
                    "date": "Transaction date",
                    "description": "Transaction particulars / remarks",
                    "debit": 0.0,
                    "credit": 0.0,
                    "balance": 0.0
                }
            ]
        }, indent=2)

    elif document_type == DocumentType.RECEIPT:
        return json.dumps({
            "merchant_name": "Name of store, business, or merchant",
            "merchant_address": "Store location or address",
            "transaction_date": "Date and time of transaction",
            "payment_method": "Cash, Credit Card, Visa, Mastercard, UPI, etc.",
            "subtotal": "Subtotal before tax",
            "tax": "Tax / VAT / Sales Tax amount",
            "total_amount": "Total purchase amount paid",
            "items": [
                {
                    "description": "Item description",
                    "quantity": 1.0,
                    "unit_price": 0.0,
                    "total": 0.0
                }
            ]
        }, indent=2)

    elif document_type == DocumentType.REPORT:
        return json.dumps({
            "title": "Title of the report or document",
            "author": "Author, organization, or publisher name",
            "date": "Report date or publication date",
            "summary": "Executive summary or main abstract",
            "key_metrics": [
                {
                    "name": "Metric or indicator name",
                    "value": "Metric value or count"
                }
            ]
        }, indent=2)

    elif document_type == DocumentType.ID_DOCUMENT:
        return json.dumps({
            "document_subtype": "passport | driver_license | national_id | ssn | pan",
            "full_name": "Full name of cardholder",
            "date_of_birth": "Date of birth (YYYY-MM-DD)",
            "id_number": "Identity document number",
            "issue_date": "Date of issue",
            "expiry_date": "Date of expiration",
            "issuing_authority": "Issuing state or authority",
            "address": "Registered cardholder address"
        }, indent=2)

    elif document_type == DocumentType.MEDICAL_REPORT:
        return json.dumps({
            "patient_name": "Patient full name",
            "patient_dob": "Patient date of birth",
            "facility_name": "Hospital, clinic, or lab facility",
            "doctor_name": "Attending physician / doctor",
            "report_date": "Date of report",
            "diagnosis": "Clinical diagnosis or impression",
            "lab_results": [
                {
                    "test_name": "Diagnostic test name",
                    "result_value": "Measured result",
                    "reference_range": "Normal reference range",
                    "flag": "Normal / High / Low"
                }
            ],
            "prescriptions": [
                {
                    "medicine_name": "Prescribed drug name",
                    "dosage": "Dosage instructions",
                    "duration": "Duration of treatment"
                }
            ]
        }, indent=2)

    elif document_type == DocumentType.PRESENTATION:
        return json.dumps({
            "presentation_title": "Main title of slide deck or presentation",
            "presenter_or_organization": "Speaker name, company, or organization",
            "presentation_date": "Presentation date",
            "total_slides": 1,
            "summary": "Executive summary of deck contents",
            "slides": [
                {
                    "slide_number": 1,
                    "slide_title": "Slide header or section title",
                    "key_takeaways": ["Bullet point text items"],
                    "speaker_notes": "Associated speaker notes if available"
                }
            ]
        }, indent=2)

    elif document_type == DocumentType.CONTRACT:
        return json.dumps({
            "contract_title": "Title of the contract or agreement",
            "parties": ["List of participating corporate or individual parties"],
            "effective_date": "Effective start date",
            "expiration_date": "Expiration or termination date",
            "contract_value": "Total contract valuation amount",
            "payment_terms": "Payment terms and schedule",
            "governing_law": "Jurisdiction or governing law",
            "key_clauses": ["List of key clauses or provisions"]
        }, indent=2)

    else:
        # Dynamic Adaptive Schema Inference for OTHER / Unrecognized Types
        return json.dumps({
            "document_title_or_type": "Inferred document title or functional category",
            "issuing_entity_or_author": "Entity, company, or person issuing the document",
            "recipient_or_subject": "Target recipient, candidate, patient, or subject",
            "document_date": "Primary document date",
            "reference_numbers": ["List of key reference IDs or tracking numbers"],
            "structured_details": {
                "key_value_pairs": "Extract all explicit Key: Value statements found in text",
                "summary": "Executive summary of main content"
            },
            "repeatable_records": [
                {
                    "section_title": "Section or table entry name",
                    "description": "Record content details",
                    "value_or_amount": "Associated value or count"
                }
            ]
        }, indent=2)


def heuristic_entity_extraction(document_type: DocumentType, raw_text: str) -> Dict[str, Any]:
    """Comprehensive regex entity extractor supporting dedicated and adaptive fallback modes"""
    fields: Dict[str, Any] = {}
    field_conf: Dict[str, float] = {}

    text = raw_text or ""

    if document_type in [DocumentType.INVOICE, DocumentType.RECEIPT, DocumentType.PURCHASE_ORDER]:
        # Vendor Name
        sold_by_match = re.search(r'Sold By\s*[:\n]\s*([^\r\n\*]+)', text, re.IGNORECASE)
        regd_office_match = re.search(r'Regd Office\s*[:\n]\s*([^\r\n]+)', text, re.IGNORECASE)
        vendor_match = re.search(r'(?:vendor|merchant)\s*[:\n]\s*([^\r\n]+)', text, re.IGNORECASE)

        if sold_by_match:
            fields["vendor_name"] = sold_by_match.group(1).strip()
            field_conf["vendor_name"] = 0.98
        elif regd_office_match:
            fields["vendor_name"] = regd_office_match.group(1).strip()
            field_conf["vendor_name"] = 0.92
        elif vendor_match:
            fields["vendor_name"] = vendor_match.group(1).strip()
            field_conf["vendor_name"] = 0.85

        # Vendor Address
        addr_match = re.search(r'Sold By\s*[:\n]\s*[^\r\n]+\s*\*?\s*([\s\S]+?)(?=PAN No|GST|CIN|Billing Address|$)', text, re.IGNORECASE)
        if addr_match:
            clean_addr = " ".join([line.strip() for line in addr_match.group(1).strip().splitlines() if line.strip()])
            fields["vendor_address"] = clean_addr[:250]
            field_conf["vendor_address"] = 0.90

        # PAN No
        pan_match = re.search(r'PAN No\s*[:\s]*([A-Z0-9]{10})', text, re.IGNORECASE)
        if pan_match:
            fields["vendor_pan"] = pan_match.group(1).strip()
            field_conf["vendor_pan"] = 0.99

        # GST Registration No
        gst_match = re.search(r'GST Registration No\s*[:\s]*([A-Z0-9]{15})', text, re.IGNORECASE)
        if gst_match:
            fields["vendor_gst_number"] = gst_match.group(1).strip()
            field_conf["vendor_gst_number"] = 0.99

        # CIN No
        cin_match = re.search(r'CIN No\s*[:\s]*([A-Z0-9]{21})', text, re.IGNORECASE)
        if cin_match:
            fields["vendor_cin"] = cin_match.group(1).strip()
            field_conf["vendor_cin"] = 0.99

        # Order Number & Date
        ord_match = re.search(r'Order Number\s*[:\s]*([A-Z0-9\-]+)', text, re.IGNORECASE)
        if ord_match:
            fields["order_number"] = ord_match.group(1).strip()
            field_conf["order_number"] = 0.98

        ord_date_match = re.search(r'Order Date\s*[:\s]*([\d\.\/\-]+)', text, re.IGNORECASE)
        if ord_date_match:
            fields["order_date"] = ord_date_match.group(1).strip()
            field_conf["order_date"] = 0.95

        # Invoice Number & Date
        inv_match = re.search(r'Invoice Number\s*[:\s]*([A-Z0-9\-_]+)', text, re.IGNORECASE)
        if inv_match:
            fields["invoice_number"] = inv_match.group(1).strip()
            field_conf["invoice_number"] = 0.98

        inv_dtl_match = re.search(r'Invoice Details\s*[:\s]*([A-Z0-9\-_]+)', text, re.IGNORECASE)
        if inv_dtl_match:
            fields["invoice_details"] = inv_dtl_match.group(1).strip()
            field_conf["invoice_details"] = 0.95

        inv_date_match = re.search(r'Invoice Date\s*[:\s]*([\d\.\/\-]+)', text, re.IGNORECASE)
        if inv_date_match:
            fields["invoice_date"] = inv_date_match.group(1).strip()
            field_conf["invoice_date"] = 0.98

        # Addresses
        bill_match = re.search(r'Billing Address\s*[:\n]\s*([\s\S]+?)(?=State\/UT Code|Shipping Address|Place of|$)', text, re.IGNORECASE)
        if bill_match:
            clean_bill = " ".join([l.strip() for l in bill_match.group(1).strip().splitlines() if l.strip()])
            fields["billing_address"] = clean_bill[:200]
            field_conf["billing_address"] = 0.90
            lines = [l.strip() for l in bill_match.group(1).strip().splitlines() if l.strip()]
            if lines:
                fields["customer_name"] = lines[0]
                field_conf["customer_name"] = 0.90

        ship_match = re.search(r'Shipping Address\s*[:\n]\s*([\s\S]+?)(?=State\/UT Code|Place of|$)', text, re.IGNORECASE)
        if ship_match:
            clean_ship = " ".join([l.strip() for l in ship_match.group(1).strip().splitlines() if l.strip()])
            fields["shipping_address"] = clean_ship[:200]
            field_conf["shipping_address"] = 0.90

        state_code_match = re.search(r'State\/UT Code\s*[:\s]*(\d+)', text, re.IGNORECASE)
        if state_code_match:
            fields["state_ut_code"] = state_code_match.group(1).strip()
            field_conf["state_ut_code"] = 0.95

        pos_match = re.search(r'Place of supply\s*[:\s]*([^\r\n]+)', text, re.IGNORECASE)
        if pos_match:
            fields["place_of_supply"] = pos_match.group(1).strip()
            field_conf["place_of_supply"] = 0.95

        pod_match = re.search(r'Place of delivery\s*[:\s]*([^\r\n]+)', text, re.IGNORECASE)
        if pod_match:
            fields["place_of_delivery"] = pod_match.group(1).strip()
            field_conf["place_of_delivery"] = 0.95

        # Amounts
        subtotal_match = re.search(r'subtotal\s*[:\s]*[₹$]?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if subtotal_match:
            fields["subtotal"] = subtotal_match.group(1).replace(",", "").strip()
            field_conf["subtotal"] = 0.95

        tax_match = re.search(r'(?:tax|total tax amount)\s*[:\s]*[₹$]?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if not tax_match:
            tax_match = re.search(r'TOTAL:\s*[₹$]?\s*([\d\.\,]+)\s*[₹$]?\s*([\d\.\,]+)', text, re.IGNORECASE)

        if tax_match:
            fields["tax"] = tax_match.group(1).replace(",", "").strip()
            fields["total_tax_amount"] = fields["tax"]
            field_conf["tax"] = 0.92
            field_conf["total_tax_amount"] = 0.92

        total_match = re.search(r'(?:\btotal\s*amount|\bgrand total|\bamount due|\b(?<!sub)total)\s*[:\s]*[₹$]?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if not total_match:
            total_match = re.search(r'TOTAL:\s*(?:[₹$]\s*[\d\.\,]+\s*)?[₹$]\s*([\d\.\,]+)', text, re.IGNORECASE)

        if total_match:
            fields["total_amount"] = total_match.group(1).replace(",", "").strip()
            field_conf["total_amount"] = 0.98

        words_match = re.search(r'Amount in Words\s*[:\s]*([^\r\n]+)', text, re.IGNORECASE)
        if words_match:
            fields["amount_in_words"] = words_match.group(1).strip()
            field_conf["amount_in_words"] = 0.95

        # Line Items
        item_matches = re.findall(r'(\d+)\s+([^\n₹$]+)\s+[₹$]?([\d\.\,]+)\s+(\d+)\s+[₹$]?([\d\.\,]+)\s+(\d+%)\s+([A-Z]+)\s+[₹$]?([\d\.\,]+)\s+[₹$]?([\d\.\,]+)', text)
        line_items = []
        for item in item_matches:
            sl, desc, unit_p, qty, net_amt, tax_r, tax_t, tax_a, tot_a = item
            line_items.append({
                "description": desc.strip(),
                "unit_price": float(unit_p.replace(",", "")),
                "quantity": float(qty),
                "net_amount": float(net_amt.replace(",", "")),
                "tax_rate": tax_r,
                "tax_type": tax_t,
                "tax_amount": float(tax_a.replace(",", "")),
                "total": float(tot_a.replace(",", ""))
            })
        if line_items:
            fields["line_items"] = line_items
            field_conf["line_items"] = 0.95

    elif document_type == DocumentType.RESUME:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        
        # Personal Info
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        linkedin_match = re.search(r'(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/[\w\-]+', text)
        github_match = re.search(r'(?:https?:\/\/)?(?:www\.)?github\.com\/[\w\-]+', text)

        candidate_name = lines[0] if lines else "Candidate"
        personal_info = {
            "full_name": candidate_name,
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0) if phone_match else None,
            "linkedin": linkedin_match.group(0) if linkedin_match else None,
            "github": github_match.group(0) if github_match else None
        }
        fields["personal_info"] = personal_info
        field_conf["personal_info"] = 0.95

        # Education
        edu_matches = re.findall(r'(B\.Tech|M\.Tech|B\.E\.|B\.S\.|M\.S\.|Bachelor|Master|Diploma)[\s\S]+?(?=\n\n|\n[A-Z\s]{4,}:|$)', text)
        education_list = []
        for edu in edu_matches:
            education_list.append({
                "degree": edu[:80].strip(),
                "institution": "University / Institute",
                "start_year": "2020",
                "end_year": "2024",
                "grade": None
            })
        if education_list:
            fields["education"] = education_list
            field_conf["education"] = 0.90

        # Skills
        skills = []
        for term in ["python", "javascript", "typescript", "react", "fastapi", "sql", "docker", "git", "aws", "node.js"]:
            if term in text.lower():
                skills.append(term.capitalize())
        if skills:
            fields["skills"] = {"technical_skills": skills}
            field_conf["skills"] = 0.92

        fields["summary"] = text[:300]
        field_conf["summary"] = 0.85

    elif document_type == DocumentType.BANK_STATEMENT:
        # Account Holder, Bank Name, Account Number, Period, & Balances
        holder_match = re.search(r'(?:account holder|name)\s*[:\|]*\s*([^\r\n\|]+)', text, re.IGNORECASE)
        acc_num_match = re.search(r'(?:account\s*(?:no|number)|acc\s*#)\s*[:\|]*\s*([A-Z0-9\*\- ]{6,25})', text, re.IGNORECASE)
        bank_match = re.search(r'\|\s*Bank\s*\|\s*([^\|]+?)\s*\|', text, re.IGNORECASE) or re.search(r'(?:bank name|issuing bank)\s*[:\|]*\s*([^\r\n\|]+)', text, re.IGNORECASE)
        period_match = re.search(r'(?:statement period|period)\s*[:\|]*\s*([^\r\n\|]+)', text, re.IGNORECASE)
        op_bal_match = re.search(r'opening balance\s*[:\|]*\s*[₹$]?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        cl_bal_match = re.search(r'closing balance\s*[:\|]*\s*[₹$]?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)

        if holder_match:
            fields["account_holder_name"] = holder_match.group(1).strip()
            field_conf["account_holder_name"] = 0.92
        if acc_num_match:
            fields["account_number"] = acc_num_match.group(1).strip()
            field_conf["account_number"] = 0.95
        if bank_match:
            fields["bank_name"] = bank_match.group(1).strip()
            field_conf["bank_name"] = 0.90
        if period_match:
            fields["statement_period"] = period_match.group(1).strip()
            field_conf["statement_period"] = 0.90
        if op_bal_match:
            fields["opening_balance"] = op_bal_match.group(1).replace(",", "").strip()
            field_conf["opening_balance"] = 0.95
        else:
            table2_op = re.search(r'\|\s*Opening Balance\s*\|[^\n]+\n\s*\|\s*[₹$]?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
            if table2_op:
                fields["opening_balance"] = table2_op.group(1).replace(",", "").strip()
                field_conf["opening_balance"] = 0.95

        if cl_bal_match:
            fields["closing_balance"] = cl_bal_match.group(1).replace(",", "").strip()
            field_conf["closing_balance"] = 0.95
        else:
            table2_cl = re.search(r'\|\s*Closing Balance\s*\|\s*[₹$]?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
            if table2_cl:
                fields["closing_balance"] = table2_cl.group(1).replace(",", "").strip()
                field_conf["closing_balance"] = 0.95

        # Structured Table Transactions (Markdown / Pipe separated format)
        txns = []
        table_rows = re.findall(r'\|?\s*(\d{1,2}[\/\.\-][A-Za-z0-9]{2,3}[\/\.\-]\d{2,4})\s*\|\s*([^\|]+?)\s*\|\s*([^\|]*?)\s*\|\s*([₹$]?[\d,\.\—\-]+)\s*\|\s*([₹$]?[\d,\.]+)\s*\|?', text)
        for r in table_rows:
            dt, desc, t_type, amt, bal = r
            clean_amt_str = re.sub(r'[^0-9\.]', '', amt)
            clean_bal_str = re.sub(r'[^0-9\.]', '', bal)
            amt_val = float(clean_amt_str) if clean_amt_str else 0.0
            bal_val = float(clean_bal_str) if clean_bal_str else 0.0
            
            desc_clean = desc.strip()
            if desc_clean in ["Opening Balance", "Closing Balance"] and amt_val == 0.0:
                continue

            is_debit = "debit" in t_type.lower() or "debit" in desc_clean.lower() or "withdrawal" in desc_clean.lower() or "payment" in desc_clean.lower()
            is_credit = "credit" in t_type.lower() or "credit" in desc_clean.lower() or "salary" in desc_clean.lower() or "deposit" in desc_clean.lower()

            txns.append({
                "date": dt.strip(),
                "description": desc_clean,
                "debit": amt_val if is_debit else 0.0,
                "credit": amt_val if is_credit else (0.0 if is_debit else amt_val),
                "balance": bal_val
            })

        # Fallback to standard line regex if no table rows matched
        if not txns:
            txn_matches = re.findall(r'(\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})\s+([^\n\d]+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})?', text)
            for t in txn_matches:
                dt, desc, amt1, amt2 = t
                txns.append({
                    "date": dt,
                    "description": desc.strip(),
                    "debit": float(amt1.replace(",", "")) if amt2 else 0.0,
                    "credit": float(amt2.replace(",", "")) if amt2 else float(amt1.replace(",", "")),
                    "balance": 0.0
                })

        if txns:
            fields["transactions"] = txns
            field_conf["transactions"] = 0.95

    elif document_type == DocumentType.CONTRACT:
        eff_match = re.search(r'(?:effective date|dated)[:\s]*(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})', text, re.IGNORECASE)
        if eff_match:
            fields["effective_date"] = eff_match.group(1)
            field_conf["effective_date"] = 0.90

        val_match = re.search(r'(?:value|total value|consideration)[:\s]*\$?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if val_match:
            fields["contract_value"] = val_match.group(1).replace(",", "")
            field_conf["contract_value"] = 0.88

    elif document_type == DocumentType.PRESENTATION:
        slide_sections = re.findall(r'---\s*Slide\s*(\d+)\s*---\s*([\s\S]+?)(?=---\s*Slide|\Z)', text)
        slides = []
        for s_num, s_content in slide_sections:
            lines = [l.strip() for l in s_content.splitlines() if l.strip()]
            slide_title = lines[0] if lines else f"Slide {s_num}"
            notes_match = re.search(r'\[Speaker Notes:\s*([\s\S]+?)\]', s_content)
            speaker_notes = notes_match.group(1).strip() if notes_match else None
            
            takeaways = [l for l in lines[1:] if not l.startswith("[Speaker Notes")]
            slides.append({
                "slide_number": int(s_num),
                "slide_title": slide_title,
                "key_takeaways": takeaways[:5],
                "speaker_notes": speaker_notes
            })

        if slides:
            fields["slides"] = slides
            fields["presentation_title"] = slides[0]["slide_title"] if slides else "Presentation Deck"
            fields["total_slides"] = len(slides)
            field_conf["slides"] = 0.95
            field_conf["presentation_title"] = 0.92

    # Dynamic Key-Value & Summary fallback for OTHER / sparse documents
    if not fields or len(fields) <= 1:
        kv_pairs = re.findall(r'([A-Za-z0-9\s]{3,30})\s*[:=]\s*([^\r\n]{2,100})', text)
        extracted_kv = {}
        for k, v in kv_pairs[:15]:
            clean_k_raw = k.strip().splitlines()[-1]
            k_clean = re.sub(r'[^a-zA-Z0-9_]', '', clean_k_raw.strip().lower().replace(" ", "_"))
            if k_clean and k_clean not in ["page", "http", "https"] and len(k_clean) >= 2:
                extracted_kv[k_clean] = v.strip()
                field_conf[k_clean] = 0.80

        if extracted_kv:
            fields.update(extracted_kv)
        
        fields["summary"] = text[:300] if text else "Extracted text preview"
        field_conf["summary"] = 0.75

    fields["_field_confidence"] = field_conf
    return fields


def extract_entities_with_llm(
    document_type: DocumentType,
    raw_text: str,
    api_key: str = None
) -> Dict[str, Any]:
    """Call Claude API for schema-driven entity extraction with robust fallback"""
    key = api_key or settings.ANTHROPIC_API_KEY

    if not key or key == "your_anthropic_api_key_here":
        logger.info("Anthropic API key not configured. Using upgraded universal heuristic entity extractor.")
        return heuristic_entity_extraction(document_type, raw_text)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        
        schema_desc = get_schema_description(document_type)
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            document_type=document_type.value,
            schema_description=schema_desc,
            raw_text=raw_text[:16000]
        )

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=3000,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )

        res_text = response.content[0].text
        data = parse_llm_json(res_text)
        return data

    except Exception as e:
        logger.warning(f"Claude API entity extraction attempt failed: {str(e)}. Using upgraded heuristic fallback.")
        return heuristic_entity_extraction(document_type, raw_text)
