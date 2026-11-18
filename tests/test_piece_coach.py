from pathlib import Path

import chess
import pytest
from fastapi.testclient import TestClient

from beyond_move.app import create_app


def test_regular_game_starts_from_standard_position_and_bot_can_open():
    with TestClient(create_app()) as client:
        start = client.post("/api/game", json={}).json()
        assert start["fen"] == chess.STARTING_FEN
        assert start["turn"] == "white"
        assert len(start["moves"]) == 20
        bot = client.post("/api/bot", json={"side": "black", "history": []})
        assert bot.status_code == 200
        board = chess.Board()
        board.push_uci(bot.json()["move"])
        assert bot.json()["fen"] == board.fen()
        assert bot.json()["turn"] == "black"


def test_bot_respects_player_turn_and_refuses_illegal_history():
    with TestClient(create_app()) as client:
        assert client.post("/api/bot", json={"side": "white", "history": []}).status_code == 409
        assert client.post("/api/game", json={"history": ["e2e5"]}).status_code == 422
        assert client.post("/api/game", json={"fen": chess.STARTING_FEN}).status_code == 422


def test_game_reports_checkmate_without_playing_again():
    history = ["f2f3", "e7e5", "g2g4", "d8h4"]
    with TestClient(create_app()) as client:
        end = client.post("/api/game", json={"history": history}).json()
        assert end["winner"] == "black" and end["outcome"] == "checkmate"
        assert end["moves"] == []
        assert (
            client.post("/api/bot", json={"side": "black", "history": history}).status_code == 409
        )


def test_after_bf5_coach_warns_about_dama_without_playing_for_black():
    payload = {
        "case_id": "queen-trade",
        "side": "black",
        "history": ["c8f5"],
        "square": "f5",
        "question": "O que fazer com o bispo depois?",
    }
    with TestClient(create_app(engine=Path("/not-installed"))) as client:
        result = client.post("/api/advice", json=payload)
        assert result.status_code == 200
        data = result.json()
        assert data["turn"] == "white" and data["move"] is None
        assert "bispo" in data["answer"].lower()
        assert "dama" in data["answer"].lower()
        assert data["threat"]["uci"] == "e2e5"
        assert client.post("/api/advice", json={**payload, "square": "a3"}).status_code == 422


def test_advice_uses_current_position_and_question_without_engine():
    with TestClient(create_app(engine=Path("/not-installed"))) as client:
        body = {"square": "f1", "question": "Meu bispo está ameaçado?"}
        first = client.post("/api/advice", json=body).json()
        second = client.post("/api/advice", json={**body, "question": "Onde posso jogar?"}).json()
        assert first["answer"] != second["answer"]
        assert first["legal_count"] == 0 and first["move"] is None
        later = client.post("/api/advice", json={**body, "history": ["e2e4", "e7e5"]}).json()
        assert later["legal_count"] > 0 and later["fen"] != first["fen"]


def test_real_engine_arrow_is_legal_and_starts_at_selected_piece():
    path = Path(".local/stockfish")
    if not path.is_file():
        pytest.skip("local Stockfish asset not installed")
    with TestClient(create_app(engine=path)) as client:
        payload = {
            "history": ["e2e4", "e7e5"],
            "square": "f1",
            "question": "O que faço com esse bispo agora?",
        }
        data = client.post("/api/advice", json=payload).json()
        assert data["source"] == "stockfish"
        assert data["move"]["uci"].startswith("f1")
        assert chess.Move.from_uci(data["move"]["uci"]) in chess.Board(data["fen"]).legal_moves
