export type DocumentStatus = 
  | 'uploaded' 
  | 'processing' 
  | 'preprocessed' 
  | 'ocr_complete' 
  | 'classified' 
  | 'extracted' 
  | 'validated' 
  | 'needs_review' 
  | 'failed';

export type DocumentType = 
  | 'invoice' 
  | 'contract' 
  | 'form' 
  | 'report' 
  | 'receipt' 
  | 'purchase_order' 
  | 'other';

export interface DocumentMetadata {
  id: string;
  filename: string;
  file_path: string;
  file_type: string;
  upload_date: string;
  status: DocumentStatus;
  document_type: DocumentType;
  page_count: number;
  confidence_score?: number;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  storage_directory?: string;
  ocr_provider?: string;
}
