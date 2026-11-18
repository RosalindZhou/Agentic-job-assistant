"""Parse the evaluator's JSON response without logging scraped content."""

import json


def extract_jobs(text: str) -> list[dict]:
    """Return valid postings from a JSON object inside a model response."""
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            continue
        jobs = obj.get("job_list") if isinstance(obj, dict) else None
        if not isinstance(jobs, list):
            continue
        return [
            job for job in jobs
            if isinstance(job, dict)
            and isinstance(job.get("title"), str) and job["title"].strip()
            and isinstance(job.get("company"), str) and job["company"].strip()
        ]
    return []
