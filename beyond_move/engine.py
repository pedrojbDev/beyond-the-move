import os
import threading
from functools import lru_cache
from pathlib import Path

import chess
import chess.engine

from .domain import play, replay

_ENGINE_LOCK = threading.Lock()


class EngineUnavailable(RuntimeError):
    """The configured UCI engine cannot return a variation."""


@lru_cache(maxsize=96)
def variation(engine: Path, case_id: str, uci: str) -> list[dict[str, str]]:
    board, candidate = play(case_id, uci)
    if not engine.is_file() or not os.access(engine, os.X_OK):
        raise EngineUnavailable("Stockfish is not installed.")
    try:
        with (
            _ENGINE_LOCK,
            chess.engine.SimpleEngine.popen_uci(str(engine.resolve()), timeout=3) as process,
        ):
            process.configure({"Threads": 1, "Hash": 16})
            result = process.analyse(
                board,
                chess.engine.Limit(nodes=25_000, time=0.5),
                root_moves=[candidate],
            )
    except (OSError, RuntimeError, TimeoutError, chess.engine.EngineError) as exc:
        raise EngineUnavailable("Stockfish could not analyze the move.") from exc
    line = result.get("pv")
    if not line or line[0] != candidate:
        raise EngineUnavailable("Stockfish returned no matching variation.")
    return replay(board, tuple(move.uci() for move in line[:5]))
