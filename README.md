# LabLens

An app that reads a blood test report (PDF or pasted text), checks the values against usual reference ranges, and explains them in plain language. It also answers follow-up questions about the report in a chat panel.

This is an educational demo project, not a medical device. It never diagnoses a condition and always tells the person to talk to a doctor.

**Live demo:** _add your Netlify link here_

## Features

- Upload a PDF report, or paste the results table as text, or try the built-in sample report
- A parser reads about 35 common tests (blood count, sugar, cholesterol, kidney, liver, thyroid, vitamins, electrolytes) with regular expressions: it finds the value on each line, and prefers the reference range printed on the report itself over a standard range
- Handles Indian number formats (`2,45,000`), counts given in thousands or lakhs, and uses male/female ranges where they differ (for example hemoglobin)
- Each result is shown as a card with a plain-language explanation, a mini range gauge, and is grouped into "Worth a look" and "All results"
- A plain-language summary of the whole report, with everyday habits and questions to ask a doctor
- A chat panel to ask follow-up questions about the report, in English, Hindi or Hinglish
- **Retrieval-augmented answers (RAG):** open-ended questions ("what foods help lower cholesterol?") search a small hand-written health-notes knowledge base and ground the answer in the matched notes, shown as a source citation under the reply. Works with or without an AI key — without one, the best matching note is returned directly
- Works with no AI key (clear rule-based explanations). Add an OpenAI or Groq key for a more personal, AI-written explanation and chat
- If the AI call fails, the server falls back to the rule-based text instead of crashing
- The report is analysed in memory and not saved on the server; only the parsed numbers (not the raw report) are sent to the AI model
- Rate limiting, and clear error messages for bad or unreadable files

## How it works

```
Browser (React)  --- POST /api/analyze (PDF / text) --->  FastAPI
                 <--- values + plain-language summary ---

                 --- POST /api/chat (question + values) --->  FastAPI
                 <--- answer ---
```

1. `backend/extract.py` pulls the text out of the PDF.
2. `backend/parser.py` searches the text for around 35 known tests, reads the value and (if present) the report's own reference range, and marks each one normal, low or high.
3. `backend/knowledge_base.py` and `backend/retrieval.py` hold a small set of health-education articles, chunked and indexed for search: TF-IDF and cosine similarity by default (no extra dependencies, works offline), or real OpenAI embeddings automatically when an OpenAI key is configured.
4. `backend/explain.py` turns the parsed values into a plain-language summary, and answers chat questions by retrieving relevant chunks (RAG) and asking the LLM to ground its answer in them — or, with no AI key, returning the best-matching note directly with its source.

## Tech

- **Frontend:** React 18, Vite, plain CSS
- **Backend:** Python, FastAPI, pypdf, OpenAI-compatible LLM client, a small RAG pipeline (chunking, TF-IDF/embeddings, cosine similarity search)
- **Tests:** pytest (parser, PDF upload, API, chat, retrieval/RAG, rate limiter)

## Run it on your computer

You need two terminals.

### 1. Backend (Python 3.10 or newer)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac / Linux
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```

Check http://localhost:8000/api/health — you should see `{"status":"ok","mode":"basic"}`.

### 2. Frontend (Node.js 20.19 or newer)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and select "Try a sample report" to see it work immediately.

### Optional: AI explanations

Copy `backend/.env.example` to `backend/.env`, uncomment the lines for your provider, and paste your key. Restart the backend; `/api/health` will show `"mode":"ai"`.

Never commit `.env` (it is already in `.gitignore`).

### Run the tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

## Deploy

**Backend on Render (free plan):** create a Web Service from this repo, Root Directory `backend`, build command `pip install -r requirements.txt`, start command `uvicorn main:app --host 0.0.0.0 --port $PORT`. Add `ALLOWED_ORIGINS` (your Netlify URL) and your LLM key if you use one.

**Frontend on Netlify:** new site from the repo, base directory `frontend`, build command `npm run build`, publish directory `dist`. Add `VITE_API_URL` with your Render address, then redeploy.

The free Render plan sleeps when idle, so the first request after a break can take up to a minute.

## Important limits (by design)

- The reference ranges are general adult ranges for education, not a medical standard. The app prefers the range printed on the report itself whenever it can find one.
- The PDF reader only works on reports with real text. A photo or a scanned image of a report will not be read.
- The parser recognises about 35 common test names. Anything else is skipped rather than guessed.
- This app never diagnoses, never recommends medicines or supplements, and always points to a doctor.

## Folder structure

```
backend/
  parser.py         Finds lab values and reference ranges in report text
  extract.py        Reads text out of an uploaded PDF
  knowledge_base.py Health-education articles used for retrieval (RAG)
  retrieval.py      Chunking, indexing and search (TF-IDF or OpenAI embeddings)
  explain.py        Plain-language summary and chat answers (RAG + AI, or rule-based)
  samples.py        The built-in fictional sample report
  main.py       FastAPI app: /api/analyze, /api/chat, /api/health
  test_app.py   tests
frontend/
  src/components/   UploadCard, Dropzone, ResultsView, ValueCard, ChatPanel ...
  src/hooks/        useReportChat.js
  src/App.jsx
```

## Ideas to extend it

- Recognise more tests, or let the person confirm a test the parser was unsure about
- A trend view across several reports over time
- Export the plain-language summary as a PDF to share with a doctor
