import axios from 'axios';
import { DocumentMetadata, HealthResponse } from '../types';

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30-second timeout to handle Render free-tier cold starts cleanly
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      console.error('API Request Timed Out:', error.config?.url);
    }
    return Promise.reject(error);
  }
);

export const fetchHealthStatus = async (): Promise<HealthResponse> => {
  const response = await apiClient.get('/health/deep', { timeout: 45000 });
  return response.data;
};



export interface UploadResponse {
  id: string;
  filename: string;
  file_type: string;
  upload_date: string;
  status: string;
  message: string;
}

export interface PipelineStatusResponse {
  document_id: string;
  filename: string;
  status: string;
  progress_percentage: number;
  current_stage: string;
  page_count: number;
  document_type: string;
}

export interface ExtractedFieldItem {
  id: string;
  document_id: string;
  field_name: string;
  field_value: string | null;
  confidence_score: number;
  data_type: string;
  bounding_box: any;
  is_validated: boolean;
  validation_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ValidationItem {
  id: string;
  rule_name: string;
  passed: boolean;
  severity: string;
  message: string;
  field_id: string | null;
}

export interface ValidationGroupedResponse {
  document_id: string;
  status: string;
  total_rules: number;
  passed_count: number;
  failed_count: number;
  errors: ValidationItem[];
  warnings: ValidationItem[];
  info: ValidationItem[];
}

export interface ProcessingLogItem {
  id: string;
  stage: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
}

export interface AnalyticsSummaryResponse {
  total_documents: number;
  validated_count: number;
  needs_review_count: number;
  processing_count: number;
  failed_count: number;
  avg_confidence_score: number;
  avg_processing_time_sec: number;
  status_counts: Record<string, number>;
  document_type_counts: Record<string, number>;
}

export interface TimeSeriesDataPoint {
  date: string;
  processed: number;
  validated: number;
  needs_review: number;
  failed: number;
}

export interface AnalyticsTimeseriesResponse {
  data_points: TimeSeriesDataPoint[];
}

export const uploadDocumentApi = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const triggerProcessDocumentApi = async (id: string): Promise<DocumentMetadata> => {
  const response = await apiClient.post(`/documents/${id}/process`);
  return response.data;
};

export const fetchDocumentApi = async (id: string): Promise<DocumentMetadata> => {
  const response = await apiClient.get(`/documents/${id}`);
  return response.data;
};

export const fetchDocumentStatusApi = async (id: string): Promise<PipelineStatusResponse> => {
  const response = await apiClient.get(`/documents/${id}/status`);
  return response.data;
};

export const fetchDocumentLogsApi = async (id: string): Promise<ProcessingLogItem[]> => {
  const response = await apiClient.get(`/documents/${id}/logs`);
  return response.data;
};

export const fetchDocumentFieldsApi = async (id: string): Promise<ExtractedFieldItem[]> => {
  const response = await apiClient.get(`/documents/${id}/fields`);
  return response.data;
};

export const updateExtractedFieldApi = async (
  documentId: string,
  fieldId: string,
  newValue: string,
  notes?: string
): Promise<ExtractedFieldItem> => {
  const response = await apiClient.patch(`/documents/${documentId}/fields/${fieldId}`, {
    field_value: newValue,
    validation_notes: notes || 'Manually corrected by reviewer',
  });
  return response.data;
};

export const overrideClassificationApi = async (
  documentId: string,
  overrideType: string
) => {
  const response = await apiClient.post(`/documents/${documentId}/classification/override`, {
    override_type: overrideType,
    reasoning: 'User manual classification override',
  });
  return response.data;
};

export const fetchDocumentValidationApi = async (id: string): Promise<ValidationGroupedResponse> => {
  const response = await apiClient.get(`/documents/${id}/validation`);
  return response.data;
};

export const triggerValidateDocumentApi = async (id: string): Promise<ValidationGroupedResponse> => {
  const response = await apiClient.post(`/documents/${id}/validate`);
  return response.data;
};

export const exportDocumentApi = async (id: string, format: 'json' | 'csv' = 'json') => {
  if (format === 'csv') {
    const response = await apiClient.get(`/documents/${id}/export?format=csv`, {
      responseType: 'blob',
    });
    return response.data;
  }
  const response = await apiClient.get(`/documents/${id}/export?format=json`);
  return response.data;
};

export const fetchAnalyticsSummaryApi = async (): Promise<AnalyticsSummaryResponse> => {
  const response = await apiClient.get('/analytics/summary');
  return response.data;
};

export const fetchAnalyticsTimeseriesApi = async (days = 30): Promise<AnalyticsTimeseriesResponse> => {
  const response = await apiClient.get(`/analytics/timeseries?days=${days}`);
  return response.data;
};
