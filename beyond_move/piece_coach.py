import hashlib
import re
import unicodedata
from pathlib import Path

import chess

from .domain import CASE_BY_ID
from .engine import EngineUnavailable, best_piece_move

PIECES = {
    chess.PAWN: "peão",
    chess.KNIGHT: "cavalo",
    chess.BISHOP: "bispo",
    chess.ROOK: "torre",
    chess.QUEEN: "dama",
    chess.KING: "rei",
}
VALUES = (0, 1, 3, 3, 5, 9, 20)


def color_name(color: chess.Color) -> str:
    return "white" if color else "black"


def board_from(history: list[str], case_id: str | None = None) -> chess.Board:
    board = CASE_BY_ID[case_id].board() if case_id is not None else chess.Board()
    for uci in history:
        if board.is_game_over():
            raise ValueError("Moves after the end of the game are not allowed.")
        board.push_uci(uci)
    return board


def snapshot(board: chess.Board) -> dict:
    outcome = board.outcome()
    return {
        "fen": board.fen(),
        "turn": color_name(board.turn),
        "moves": sorted(move.uci() for move in board.legal_moves) if not outcome else [],
        "check": board.is_check(),
        "outcome": outcome.termination.name.lower() if outcome else None,
        "winner": color_name(outcome.winner) if outcome and outcome.winner is not None else None,
    }


def move_info(board: chess.Board, move: chess.Move) -> dict[str, str]:
    return {"uci": move.uci(), "san": board.san(move)}


def captured(board: chess.Board, move: chess.Move) -> chess.Piece | None:
    if board.is_en_passant(move):
        return chess.Piece(chess.PAWN, not board.turn)
    return board.piece_at(move.to_square)


def simple_move(board: chess.Board) -> chess.Move:
    def priority(move: chess.Move) -> tuple[int, bytes]:
        target = captured(board, move)
        origin = board.piece_type_at(move.from_square) or chess.PAWN
        after = board.copy(stack=False)
        after.push(move)
        gain = 3 * VALUES[target.piece_type] if target else 0
        if after.attackers(after.turn, move.to_square):
            gain -= VALUES[origin]
        if move.promotion:
            gain += VALUES[move.promotion]
        tie = hashlib.sha256(f"{board.fen()}|{move.uci()}".encode()).digest()
        return gain, tie

    return max(board.legal_moves, key=priority)


def question_focus(question: str) -> str:
    text = unicodedata.normalize("NFKD", question.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    if re.search(r"ameac|atacad|proteg|defes|defend|segur|perigo|pendur|captur", text):
        return "safety"
    if re.search(r"onde|casas?|opcoes|possive|leg(?:al|ais)|quantos|quantas", text):
        return "mobility"
    return "plan"


def advice(
    board: chess.Board,
    square: chess.Square,
    player: chess.Color,
    question: str,
    engine: Path,
) -> dict:
    piece = board.piece_at(square)
    if piece is None:
        raise ValueError("Select an occupied square.")
    side = "brancas" if board.turn else "pretas"
    name = PIECES[piece.piece_type]
    label = f"{name} em {chess.square_name(square)}"
    focus = question_focus(question)
    result = {
        "fen": board.fen(),
        "turn": color_name(board.turn),
        "piece": name,
        "legal_count": 0,
        "focus": focus,
        "source": "board",
        "move": None,
        "threat": None,
        "answer": "",
        "why": "",
    }
    if board.is_game_over():
        result["answer"] = f"A partida terminou; não há próximo lance para {label}."
        return result

    moves = tuple(move for move in board.legal_moves if move.from_square == square)
    result["legal_count"] = len(moves)
    opponents = board.attackers(not piece.color, square)
    allies = board.attackers(piece.color, square)
    safety = (
        f"Peças adversárias que atacam a casa: {len(opponents)}. "
        f"Peças aliadas que cobrem a casa: {len(allies)}."
    )
    if board.turn != player:
        answer = f"É a vez das {side}. Espere a resposta antes de decidir sobre o {label}."
        if piece.color == player:
            captures = [move for move in board.legal_moves if board.is_capture(move)]
            if captures:
                threat = max(
                    captures,
                    key=lambda move: VALUES[captured(board, move).piece_type],
                )
                target = captured(board, threat)
                result["threat"] = move_info(board, threat)
                answer += (
                    f" Antes de pensar no {name}, observe que o adversário pode capturar "
                    f"{'a ' if target.piece_type in (chess.QUEEN, chess.ROOK) else 'o '}"
                    f"{PIECES[target.piece_type]} com {board.san(threat)}."
                )
                result["why"] = (
                    "A seta mostra uma captura que o adversário pode jogar, não o seu lance."
                )
        if not result["why"]:
            result["why"] = safety
        result["answer"] = answer
        return result

    if piece.color != player:
        result["answer"] = f"O {label} é do adversário. Você não pode movê-lo."
        result["why"] = safety
        return result

    if not moves:
        result["answer"] = f"O {label} não tem lance legal nesta posição."
        result["why"] = (
            "Você está em xeque: o próximo lance precisa salvar o rei."
            if board.is_check()
            else "A peça está bloqueada ou movê-la deixaria o rei em xeque."
        )
        if focus == "safety":
            result["answer"] = safety
            result["why"] = f"O {label} não tem lance legal agora."
        return result

    if focus == "safety":
        result["answer"] = f"Sobre o {label}: {safety}"
        result["why"] = "Uma casa atacada não significa, por si só, que a captura vale a pena."
        return result
    if focus == "mobility":
        destinations = ", ".join(sorted({chess.square_name(move.to_square) for move in moves}))
        result["answer"] = f"Casas disponíveis para o {label}: {destinations}."
        result["why"] = "São destinos legais nesta posição, não uma ordem de preferência."
        return result
    try:
        move, reply = best_piece_move(engine, board, moves)
    except EngineUnavailable:
        result["answer"] = (
            f"O {label} tem {len(moves)} lance(s) legal(is), mas o Stockfish está indisponível."
        )
        result["why"] = safety
        return result
    result["source"] = "stockfish"
    result["move"] = move_info(board, move)
    result["answer"] = f"Se quiser jogar com o {label}, analise {board.san(move)}."
    after = board.copy(stack=False)
    after.push(move)
    if after.is_checkmate():
        reason = "Esse lance dá xeque-mate."
    elif board.gives_check(move):
        reason = "Esse lance dá xeque e obriga o adversário a responder."
    elif target := captured(board, move):
        reason = f"Esse lance captura uma peça adversária ({PIECES[target.piece_type]})."
    else:
        destination = chess.square_name(move.to_square)
        reason = (
            f"Em {destination}, a peça fica sob ataque."
            if after.attackers(after.turn, move.to_square)
            else f"Em {destination}, a peça não fica imediatamente atacada."
        )
    if reply is not None:
        reason += f" Uma resposta na linha analisada é {after.san(reply)}."
    result["why"] = reason + " A busca comparou lances desta peça, não todos os planos."
    return result
