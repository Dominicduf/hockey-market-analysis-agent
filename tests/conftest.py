import os

import pytest

os.environ.setdefault("OPENROUTER_API_KEY", "sk-test-dummy-key")

from app.schemas import AspectScore, SentimentResult  # noqa: E402


@pytest.fixture
def sample_sentiment_result() -> SentimentResult:
    return SentimentResult(
        product_id="bauer_supreme_stick",
        product_name="Bauer Supreme UltraSonic Hockey Stick",
        overall_score=0.7,
        sentiment_distribution={"positive": 6, "neutral": 1, "negative": 2},
        aspects={
            "performance": AspectScore(score=0.9, summary="Excellent shot pop and balance"),
            "durability": AspectScore(score=0.3, summary="Some blade chipping reported"),
            "value_for_money": AspectScore(score=0.5, summary="Pricey for recreational players"),
            "comfort": AspectScore(score=0.8, summary="Premium feel out of the box"),
            "fit": AspectScore(score=0.8, summary="Great hand fit"),
        },
        top_praised=["performance", "comfort", "fit"],
        top_complaints=["durability", "price", "blade chipping"],
        review_count=9,
    )


@pytest.fixture
def sample_sentiment_json(sample_sentiment_result: SentimentResult) -> str:
    return sample_sentiment_result.model_dump_json()
