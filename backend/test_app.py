import io
import os

os.environ.pop("LLM_API_KEY", None)  # the tests run in basic mode, without calling any AI service
os.environ.pop("OPENAI_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

import explain  # noqa: E402
from main import RateLimiter, app  # noqa: E402
from parser import assess, parse_report  # noqa: E402
from samples import SAMPLE_REPORT  # noqa: E402

client = TestClient(app)


def by_key(values):
    return {v["key"]: v for v in values}


# ---- parser
def test_sample_report_is_read_correctly():
    v = by_key(parse_report(SAMPLE_REPORT, "female"))
    assert len(v) == 25
    assert v["hemoglobin"]["status"] == "low"
    assert v["hba1c"]["status"] == "high"
    assert v["ldl"]["status"] == "high" and v["ldl"]["severity"] == "marked"
    assert v["hdl"]["status"] == "low"
    assert v["vit_d"]["status"] == "low"
    assert v["b12"]["status"] == "normal"
    assert v["platelets"]["value"] == 245000  # Indian number format 2,45,000


def test_similar_test_names_are_not_mixed_up():
    text = "HbA1c 5.4 %\nMean Corpuscular Hemoglobin (MCH) 29 pg\nNon-HDL Cholesterol 120 mg/dL\nVLDL Cholesterol 20 mg/dL"
    v = by_key(parse_report(text))
    assert v["hba1c"]["value"] == 5.4
    assert "hemoglobin" not in v and v["mch"]["value"] == 29
    assert v["nonhdl"]["value"] == 120 and v["vldl"]["value"] == 20
    assert "hdl" not in v and "total_chol" not in v


def test_standard_range_is_used_when_the_report_has_none_and_sex_matters():
    text = "Hemoglobin 12.5 g/dL"
    assert by_key(parse_report(text, "male"))["hemoglobin"]["status"] == "low"     # men: 13 to 17
    assert by_key(parse_report(text, "female"))["hemoglobin"]["status"] == "normal"  # women: 12 to 15
    assert by_key(parse_report(text))["hemoglobin"]["range_source"] == "standard"


def test_counts_written_in_thousands_are_scaled():
    v = by_key(parse_report("WBC 7.4 10^3/uL\nPlatelet Count 2.5 lakhs/cumm"))
    assert v["wbc"]["value"] == 7400
    assert v["platelets"]["value"] == 250000


def test_a_different_unit_is_not_judged_with_the_wrong_range():
    v = by_key(parse_report("Glucose, Fasting 5.8 mmol/L"))["glucose_fasting"]
    assert v["status"] == "unknown"
    assert v["unit"].lower() == "mmol/l"


def test_assess_severity():
    assert assess(105, 70, 99) == ("high", "mild")
    assert assess(140, 70, 99) == ("high", "marked")
    assert assess(85, 70, 99) == ("normal", "normal")


def test_text_without_results_gives_an_empty_list():
    assert parse_report("Patient name: John\nDate: 12 Jan 2026") == []


# ---- API
def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200 and res.json()["mode"] == "basic"


def test_analyze_sample():
    res = client.post("/api/analyze", data={"use_sample": "true", "age": "34", "sex": "female"})
    assert res.status_code == 200
    body = res.json()
    assert body["counts"]["low"] >= 3 and body["counts"]["high"] >= 3
    assert body["summary"]["source"] == "basic"
    assert "Worth a closer look" in body["summary"]["text"]
    assert "not a diagnosis" in body["disclaimer"]


def test_analyze_pasted_text():
    res = client.post("/api/analyze", data={"text": "Hemoglobin 9.0 g/dL 12 - 15"})
    assert res.status_code == 200
    assert res.json()["values"][0]["status"] == "low"


def test_analyze_pdf_upload():
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    y = 800
    for line in SAMPLE_REPORT.splitlines()[:14]:
        pdf.drawString(40, y, line)
        y -= 16
    pdf.save()
    res = client.post("/api/analyze", files={"file": ("report.pdf", buffer.getvalue(), "application/pdf")})
    assert res.status_code == 200
    assert "hemoglobin" in by_key(res.json()["values"])


def test_analyze_rejects_bad_input():
    assert client.post("/api/analyze", data={}).status_code == 422  # nothing given
    both = client.post("/api/analyze", data={"text": "Hemoglobin 12", "use_sample": "true"})
    assert both.status_code == 422  # two reports at once
    fake = client.post("/api/analyze", files={"file": ("x.pdf", b"not a pdf at all", "application/pdf")})
    assert fake.status_code == 422 and "not a PDF" in fake.json()["detail"]
    empty = client.post("/api/analyze", data={"text": "Patient: John, date 12 Jan"})
    assert empty.status_code == 422
    big = client.post("/api/analyze", files={"file": ("big.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024 + 10), "application/pdf")})
    assert big.status_code == 413
    assert client.post("/api/analyze", data={"use_sample": "true", "age": "500"}).status_code == 422


def test_chat_explains_the_test_that_was_asked_about():
    values = client.post("/api/analyze", data={"use_sample": "true"}).json()["values"]
    res = client.post("/api/chat", json={"question": "What does my hemoglobin mean?", "values": values})
    assert res.status_code == 200
    answer = res.json()["answer"]
    assert "Hemoglobin" in answer and "low" in answer


def test_chat_uses_retrieval_for_an_open_ended_question_and_returns_a_citation():
    values = client.post("/api/analyze", data={"use_sample": "true"}).json()["values"]
    res = client.post("/api/chat", json={"question": "What foods help lower cholesterol?", "values": values})
    assert res.status_code == 200
    body = res.json()
    assert "fibre" in body["answer"].lower() or "cholesterol" in body["answer"].lower()
    assert len(body["citations"]) >= 1
    assert body["citations"][0]["title"] == "Cholesterol and heart health"


def test_chat_gives_no_citation_for_an_unrelated_question():
    res = client.post("/api/chat", json={"question": "Tell me a joke about cats", "values": []})
    assert res.status_code == 200
    assert res.json()["citations"] == []


def test_chat_validates_input():
    assert client.post("/api/chat", json={"question": "", "values": []}).status_code == 422
    bad = {"question": "hi", "values": [{"key": "x", "name": "x", "value": 1, "status": "weird"}]}
    assert client.post("/api/chat", json=bad).status_code == 422


def test_basic_answer_for_open_questions_is_honest():
    assert "AI key" in explain.basic_answer("Tell me a joke about cats", [])


def test_basic_answer_uses_retrieval_when_relevant():
    text = explain.basic_answer("What foods help lower cholesterol?", [])
    assert "cholesterol" in text.lower() and "Source:" in text


def test_rate_limiter():
    limiter = RateLimiter(limit=2, window=60)
    assert [limiter.allow("a") for _ in range(3)] == [True, True, False]
    assert limiter.allow("b")


# ---- retrieval (RAG)
def test_retrieval_finds_the_right_article():
    from retrieval import retrieve
    hits = retrieve("why is my hemoglobin low", k=2)
    assert hits and hits[0]["title"] == "Anemia and iron"


def test_retrieval_returns_nothing_for_unrelated_text():
    from retrieval import retrieve
    assert retrieve("what is the capital of France", k=3) == []


def test_retrieval_does_not_return_the_same_article_twice():
    from retrieval import retrieve
    hits = retrieve("cholesterol and heart risk, what should I eat, how does diet help", k=5)
    ids = [h["article_id"] for h in hits]
    assert len(ids) == len(set(ids))
