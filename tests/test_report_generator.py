from unittest.mock import patch

from app.tools.report_generator import generate_report


def test_single_result_generates_pdf_on_disk(sample_sentiment_json, tmp_path):
    with patch("app.tools.report_generator.REPORTS_DIR", tmp_path):
        generate_report.invoke({"sentiment_results": [sample_sentiment_json]})

    pdfs = list(tmp_path.glob("*.pdf"))
    assert len(pdfs) == 1
    assert pdfs[0].stat().st_size > 0


def test_return_value_contains_filename_and_download_path(sample_sentiment_json, tmp_path):
    with patch("app.tools.report_generator.REPORTS_DIR", tmp_path):
        result = generate_report.invoke({"sentiment_results": [sample_sentiment_json]})

    assert "GET /reports/" in result
    assert ".pdf" in result


def test_multiple_results_produce_a_single_pdf(sample_sentiment_result, tmp_path):
    second = sample_sentiment_result.model_copy(
        update={"product_id": "warrior_covert_stick", "product_name": "Warrior Covert QRE 10"}
    )
    with patch("app.tools.report_generator.REPORTS_DIR", tmp_path):
        generate_report.invoke(
            {
                "sentiment_results": [
                    sample_sentiment_result.model_dump_json(),
                    second.model_dump_json(),
                ]
            }
        )

    assert len(list(tmp_path.glob("*.pdf"))) == 1


def test_invalid_json_returns_tool_error_without_creating_pdf(tmp_path):
    with patch("app.tools.report_generator.REPORTS_DIR", tmp_path):
        result = generate_report.invoke({"sentiment_results": ["this is not valid json"]})

    assert "[TOOL ERROR]" in result
    assert list(tmp_path.glob("*.pdf")) == []
