from typing import Annotated

from pydantic import BaseModel, Field

ScoreFloat = Annotated[float, Field(ge=-1.0, le=1.0)]


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    response: str


class SentimentResult(BaseModel):
    product_name: str = Field(description="The full product name as it appears in the product data")
    overall_score: ScoreFloat = Field(
        description=(
            "Overall sentiment score from -1.0 (very negative) to 1.0 (very positive),"
            " derived from the review ratings"
        )
    )
    summary: str = Field(
        description=(
            "2-3 sentence summary of customer sentiment, grounded strictly in the review text"
        )
    )


class SentimentResults(BaseModel):
    results: list[SentimentResult] = Field(
        description="Sentiment analysis results, one entry per product"
    )
