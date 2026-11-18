from pathlib import Path

import chess
from fastapi.testclient import TestClient


def client(engine=None):
    from beyond_move.app import create_app

    return TestClient(create_app(engine=engine))


def first(c):
    return c.get("/api/cases").json()[0]


def test_prepared_cases_have_only_legal_candidate_moves():
    with client() as c:
        cases = c.get("/api/cases").json()
        assert len(cases) >= 3
        assert {row["turn"] for row in cases} == {"white", "black"}
        for item in cases:
            board = chess.Board(item["fen"])
            assert board.is_valid()
            assert item["moves"]
            assert all(chess.Move.from_uci(move) in board.legal_moves for move in item["moves"])


def test_illegal_move_and_unknown_case_rejected_before_engine():
    with client(Path("/not-installed")) as c:
        assert (
            c.post("/api/reveal", json={"case_id": first(c)["id"], "move": "a1a8"}).status_code
            == 422
        )
        assert c.post("/api/reveal", json={"case_id": "unknown", "move": "e2e4"}).status_code == 404


def test_distinct_intents_and_no_engine_line_in_hint():
    with client() as c:
        row = first(c)
        body = {"case_id": row["id"], "move": row["example_move"]}
        a = c.post("/api/hint", json={**body, "reason": "Quero trocar as damas"}).json()
        b = c.post("/api/hint", json={**body, "reason": "Achei que a captura era de graça"}).json()
        assert a["focus"] == "troca"
        assert b["focus"] == "captura"
        assert a["hint"] != b["hint"]
        assert "line" not in a and "line" not in b
        assert a["source"] == b["source"] == "rules"


def test_missing_engine_for_reveal_is_distinct():
    with client(Path("/not-installed")) as c:
        row = first(c)
        response = c.post("/api/reveal", json={"case_id": row["id"], "move": row["example_move"]})
        assert response.status_code == 503


def test_black_board_replay_uses_san_and_resulting_fens():
    from beyond_move.domain import replay

    board = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
    result = replay(board, ("c7c5", "g1f3"))
    assert result[0]["san"] == "c5"
    assert result[1]["san"] == "Nf3"
    assert chess.Board(result[0]["fen"]).turn == chess.WHITE
    assert chess.Board(result[1]["fen"]).turn == chess.BLACK
    assert board.turn == chess.BLACK
