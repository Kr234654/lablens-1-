"""FastAPI server for LabLens: upload a blood report, get a plain-language explanation, ask follow-up questions."""
import asyncio
import logging
import os
import time
from collections import defaultdict, deque
from typing import List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import explain
from extract import ReportError, pdf_to_text
from parser import parse_report
from samples import SAMPLE_REPORT

load_dotenv()
log = logging.getLogger("uvicorn.error")

MAX_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_TEXT = 60_000
LANGUAGES = ("English", "Hindi", "Hinglish")

app = FastAPI(title="LabLens API")

origins = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
).split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])


class RateLimiter:
    """Allows `limit` requests per `window` seconds for each visitor, so nobody can run up the AI bill."""

    def __init__(self, limit: int, window: int = 60):
        self.limit, self.window, self.hits = limit, window, defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


limiter = RateLimiter(int(os.getenv("RATE_LIMIT_PER_MIN", "15")))


def check_rate(request: Request) -> None:
    forwarded = request.headers.get("x-forwarded-for")  # set by hosting platforms such as Render
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    if not limiter.allow(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute and try again.")


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": explain.MODE}


@app.post("/api/analyze")
async def analyze(
    request: Request,
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    use_sample: bool = Form(False),
    age: Optional[int] = Form(None),
    sex: Optional[str] = Form(None),
    language: str = Form("English"),
):
    """Read a report (PDF, pasted text or the built-in sample), find the values and explain them."""
    check_rate(request)

    sources = [bool(file and file.filename), bool(text and text.strip()), use_sample]
    if sum(sources) != 1:
        raise HTTPException(status_code=422, detail="Please give one report: upload a PDF, paste the text, or use the sample.")
    if age is not None and not 1 <= age <= 120:
        raise HTTPException(status_code=422, detail="Age must be between 1 and 120.")
    sex = sex if sex in ("male", "female") else None
    language = language if language in LANGUAGES else "English"

    try:
        if use_sample:
            report_text = SAMPLE_REPORT
        elif text and text.strip():
            if len(text) > MAX_TEXT:
                raise HTTPException(status_code=413, detail="That text is too long. Please paste only the results table.")
            report_text = text
        else:
            data = await file.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise HTTPException(status_code=413, detail="That file is larger than 5 MB.")
            report_text = await asyncio.to_thread(pdf_to_text, data)
    except ReportError as err:
        raise HTTPException(status_code=422, detail=str(err))

    values = parse_report(report_text, sex)
    if not values:
        raise HTTPException(
            status_code=422,
            detail="I could not find any known test results in this report. Try pasting the results table as text.",
        )

    summary, source = await asyncio.to_thread(explain.summarize, values, age, sex, language)
    counts = {status: sum(1 for v in values if v["status"] == status) for status in ("normal", "low", "high", "unknown")}
    return {
        "mode": explain.MODE,
        "values": values,
        "counts": counts,
        "summary": {"text": summary, "source": source},
        "disclaimer": explain.DISCLAIMER,
    }


class ChatValue(BaseModel):
    key: str = Field(max_length=30)
    name: str = Field(max_length=60)
    value: float
    unit: str = Field(default="", max_length=20)
    low: Optional[float] = None
    high: Optional[float] = None
    status: Literal["normal", "low", "high", "unknown"]
    severity: Literal["normal", "mild", "moderate", "marked"] = "normal"
    note: str = Field(default="", max_length=600)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    values: List[ChatValue] = Field(max_length=60)
    summary: str = Field(default="", max_length=6000)
    history: List[dict] = Field(default_factory=list)
    language: str = "English"


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request):
    """Answer a follow-up question about the report. The browser sends the values back, so the server stores nothing."""
    check_rate(request)
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Please type a question.")
    values = [v.model_dump() for v in body.values]
    history = [
        {"role": t["role"], "text": t["text"][:1000]}
        for t in body.history[-8:]
        if isinstance(t, dict) and t.get("role") in ("user", "bot") and isinstance(t.get("text"), str)
    ]
    language = body.language if body.language in LANGUAGES else "English"
    text, source, citations = await asyncio.to_thread(explain.answer, question, values, body.summary, history, language)
    return {"answer": text, "source": source, "citations": citations}
