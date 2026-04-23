from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    response: str


class AspectScore(BaseModel):
    score: float  # -1.0 (very negative) to 1.0 (very positive)
    summary: str  # one-line explanation


class SentimentResult(BaseModel):
    product_id: str
    product_name: str
    overall_score: float  # -1.0 to 1.0, for bar chart
    sentiment_distribution: dict[
        str, int
    ]  # {"positive": n, "neutral": n, "negative": n}, for donut chart
    aspects: dict[str, AspectScore]  # {"durability": AspectScore, ...}, for radar chart
    top_praised: list[str]  # recurring positive themes
    top_complaints: list[str]  # recurring negative themes
    review_count: int
