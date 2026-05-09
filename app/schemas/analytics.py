from pydantic import BaseModel


class AnalyticsSummaryResponse(BaseModel):
    total_requests: int
    completed_requests: int
    failed_requests: int
    total_estimated_cost: int
    total_final_cost: int
    cache_hits: int


class AnalyticsUsageItem(BaseModel):
    status: str
    count: int


class AnalyticsUsageResponse(BaseModel):
    items: list[AnalyticsUsageItem]


class AnalyticsCostItem(BaseModel):
    transaction_type: str
    amount: int
    count: int


class AnalyticsCostResponse(BaseModel):
    items: list[AnalyticsCostItem]


class AnalyticsModelItem(BaseModel):
    model_code: str
    count: int
    final_cost: int


class AnalyticsModelsResponse(BaseModel):
    items: list[AnalyticsModelItem]
