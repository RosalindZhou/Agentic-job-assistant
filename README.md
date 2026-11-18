# Agentic Job Assistant

A Python prototype that collects AI internship listings, filters them with a language model, and presents the results in a local dashboard. Its default search targets Chinese-language job boards.

## Workflow

1. The LangGraph agent chooses a search or evaluation action.
2. A Chromium browser session collects listing text.
3. The evaluator extracts and filters candidate postings. State reducers deduplicate results.
4. A reflection step updates search guidance. The run exports local CSV and JSON results and serves a dashboard.

## Setup and usage

From the repository root, activate a Python virtual environment and install the dependencies. A compatible local Chrome or Chromium browser and network access are required.

```sh
python -m pip install -r requirements.txt
python main.py
```

Before running the entry point, copy `.env.example` to `.env` and configure at least one provider key: `SILICON_API_KEY`, `GROQ_API_KEY`, or `GEMINI_API_KEY`. The dashboard starts on port 8000 after collection. Press Ctrl+C to stop it.

## Limitations

Listing collection depends on site layouts and browser availability. Model filtering can omit relevant postings or retain unrelated ones. Review results against the original listings.

Run the offline parser tests with `python -m unittest discover -s tests`.
