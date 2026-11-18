import logging
import os
import threading
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .coaching import fallback, parse_hint
from .domain import CASES, facts_for, play, replay
from .engine import EngineUnavailable, variation

STATIC = Path(__file__).parent / "static"
LOGGER = logging.getLogger(__name__)
_MODEL_LOCK = threading.Lock()


class MoveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1, max_length=32)
    move: str = Field(pattern=r"^[a-h][1-8][a-h][1-8][qrbn]?$")


class HintIn(MoveIn):
    reason: str = Field(min_length=3, max_length=280)


def _legal(body: MoveIn):
    try:
        return play(body.case_id, body.move)
    except KeyError as exc:
        raise HTTPException(404, "Unknown exercise.") from exc
    except ValueError as exc:
        raise HTTPException(422, "Illegal move in this position.") from exc


def create_app(
    engine: Path | None = None, coach: Callable[[str, str], str] | None = None
) -> FastAPI:
    app = FastAPI(title="Beyond the Move", version="1.0.0")
    binary = engine or Path(os.environ.get("STOCKFISH_PATH", ".local/stockfish"))

    @app.get("/api/cases")
    def cases():
        return [case.public() for case in CASES]

    @app.post("/api/hint")
    def hint(body: HintIn):
        board, move = _legal(body)
        if not body.reason.strip() or len(body.reason.strip()) < 3:
            raise HTTPException(422, "Write a brief reason.")
        if coach:
            try:
                result = parse_hint(coach(body.reason, facts_for(board, move)))
            except (ImportError, OSError, RuntimeError, ValueError) as exc:
                LOGGER.warning("Coaching model unavailable: %s", type(exc).__name__)
                result = None
            if result:
                return {"focus": result[0], "hint": result[1], "source": "adapter"}
        return fallback(body.reason)

    @app.post("/api/preview")
    def preview(body: MoveIn):
        board, move = _legal(body)
        return replay(board, (move.uci(),))[0]

    @app.post("/api/reveal")
    def reveal(body: MoveIn):
        _legal(body)
        try:
            return {"line": variation(binary, body.case_id, body.move)}
        except EngineUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

    if STATIC.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC), name="static")

        @app.get("/", include_in_schema=False)
        def homepage():
            return FileResponse(STATIC / "index.html")

    return app


@lru_cache(maxsize=1)
def _local_model():
    from .training import load_coach

    return load_coach(
        Path(os.environ.get("COACH_BASE_PATH", ".local/base")),
        Path(os.environ["COACH_ADAPTER_PATH"]),
    )


def _local_coach(reason: str, facts: str) -> str:
    from .training import generate_batch

    with _MODEL_LOCK:
        model, tokenizer = _local_model()
        return generate_batch(model, tokenizer, [{"reason": reason, "facts": facts}])[0]


app = create_app(coach=_local_coach if os.environ.get("COACH_ADAPTER_PATH") else None)
