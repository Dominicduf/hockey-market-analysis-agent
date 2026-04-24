import os

import pytest

os.environ.setdefault("OPENROUTER_API_KEY", "sk-test-dummy-key")

from app.schemas import SentimentResult  # noqa: E402


@pytest.fixture
def sample_sentiment_result() -> SentimentResult:
    return SentimentResult(
        product_name="Bauer Supreme UltraSonic Hockey Stick",
        overall_score=0.7,
        summary=(
            "Customers praised the stick's excellent shot power and comfortable feel. "
            "Some reviewers noted durability concerns around blade chipping. "
            "Overall sentiment is positive."
        ),
    )


@pytest.fixture
def sample_sentiment_json(sample_sentiment_result: SentimentResult) -> str:
    return sample_sentiment_result.model_dump_json()
