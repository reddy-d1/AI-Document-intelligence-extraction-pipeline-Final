from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.analytics import AnalyticsSummaryResponse, AnalyticsTimeseriesResponse
from app.services.analytics_service import get_analytics_summary, get_analytics_timeseries

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_pipeline_analytics_summary(db: Session = Depends(get_db)):
    """Retrieve aggregate document intelligence pipeline summary metrics"""
    return get_analytics_summary(db)


@router.get("/timeseries", response_model=AnalyticsTimeseriesResponse)
def get_pipeline_analytics_timeseries(days: int = 30, db: Session = Depends(get_db)):
    """Retrieve time series document volume and validation health trend metrics"""
    return get_analytics_timeseries(db, days=days)
