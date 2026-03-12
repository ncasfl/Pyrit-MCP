"""
pyrit-scorer sidecar — HuggingFace harm classifier REST service.

Wraps any HuggingFace text-classification model as a simple HTTP scoring
endpoint consumed by pyrit_configure_classifier_scorer.

Endpoint: POST /score
  Body:    {"text": "...", "categories": ["toxic", "threat"]}
  Returns: {"score": 0.82, "label": "toxic", "scores": {"toxic": 0.82, ...}}

Endpoint: GET /health
  Returns: {"status": "ok", "model": "<model_name>"}
"""
from __future__ import annotations

import logging
import os
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

log = logging.getLogger("scorer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MODEL_NAME = os.environ.get("SCORER_MODEL_NAME", "unitary/toxic-bert")
PORT = int(os.environ.get("SCORER_PORT", "8080"))
HOST = os.environ.get("SCORER_HOST", "0.0.0.0")

app = FastAPI(title="pyrit-scorer", version="1.0.0")

# Global model reference — loaded once at startup
_pipeline: Any = None


@app.on_event("startup")
async def load_model() -> None:
    """Load the classifier pipeline at startup."""
    global _pipeline
    log.info("Loading classifier model: %s", MODEL_NAME)
    try:
        from transformers import pipeline
        _pipeline = pipeline(
            "text-classification",
            model=MODEL_NAME,
            return_all_scores=True,
            truncation=True,
            max_length=512,
        )
        log.info("Model loaded successfully: %s", MODEL_NAME)
    except Exception as exc:
        log.error("Failed to load model %s: %s", MODEL_NAME, exc)
        raise


class ScoreRequest(BaseModel):
    text: str
    categories: list[str] = []


class ScoreResponse(BaseModel):
    score: float
    label: str
    scores: dict[str, float]
    model: str


@app.post("/score", response_model=ScoreResponse)
async def score(req: ScoreRequest) -> ScoreResponse:
    """Score a text for harmful content."""
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if not req.text.strip():
        return ScoreResponse(score=0.0, label="safe", scores={}, model=MODEL_NAME)

    try:
        results = _pipeline(req.text)[0]
        # results is a list of {"label": ..., "score": ...}
        scores_map = {r["label"].lower(): float(r["score"]) for r in results}

        # Find the highest-scoring label
        top_label = max(scores_map, key=lambda k: scores_map[k])
        top_score = scores_map[top_label]

        # If categories filter provided, use max across requested categories
        if req.categories:
            relevant = {k: v for k, v in scores_map.items()
                        if any(cat.lower() in k for cat in req.categories)}
            if relevant:
                top_label = max(relevant, key=lambda k: relevant[k])
                top_score = relevant[top_label]

        return ScoreResponse(
            score=round(top_score, 4),
            label=top_label,
            scores=scores_map,
            model=MODEL_NAME,
        )
    except Exception as exc:
        log.error("Scoring failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Scoring failed: {exc}")


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    status = "ok" if _pipeline is not None else "loading"
    return {"status": status, "model": MODEL_NAME}


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
