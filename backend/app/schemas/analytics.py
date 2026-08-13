from typing import List, Dict
from pydantic import BaseModel, Field


class AnalyticsSummaryResponse(BaseModel):
    total_documents: int
    validated_count: int
    needs_review_count: int
    processing_count: int
    failed_count: int
    avg_confidence_score: float
    avg_processing_time_sec: float
    status_counts: Dict[str, int] = Field(default_factory=dict)
    document_type_counts: Dict[str, int] = Field(default_factory=dict)


class TimeSeriesDataPoint(BaseModel):
    date: str
    processed: int
    validated: int
    needs_review: int
    failed: int


class AnalyticsTimeseriesResponse(BaseModel):
    data_points: List[TimeSeriesDataPoint] = Field(default_factory=list)
