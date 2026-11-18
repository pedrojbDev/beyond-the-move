from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class Case:
    id: str
    fen: str
    setup: str
    example_move: str
    title: str

    def board(self) -> chess.Board:
        board = chess.Board(self.fen)
        board.push_uci(self.setup)
        return board

    def public(self) -> dict:
        board = self.board()
        return {
            "id": self.id,
            "fen": board.fen(),
            "turn": "white" if board.turn else "black",
            "moves": sorted(move.uci() for move in board.legal_moves),
            "example_move": self.example_move,
            "title": self.title,
        }


# An original teaching setup followed by two CC0 sample rows from
# database.lichess.org/#puzzles. Candidate moves are not necessarily best.
CASES = (
    Case(
        "queen-trade",
        "rnb1kbnr/ppp1pppp/8/4q3/8/2N5/PPPP1PPP/R1BQKBNR w KQkq - 2 4",
        "d1e2",
        "e5e2",
        "Trocar ou ganhar material?",
    ),
    Case(
        "00sHx",
        "q3k1nr/1pp1nQpp/3p4/1P2p3/4P3/B1PP1b2/B5PP/5K2 b k - 0 17",
        "e8d7",
        "f7g8",
        "Uma captura tentadora",
    ),
    Case(
        "00sJ9",
        "r3r1k1/p4ppp/2p2n2/1p6/3P1qb1/2NQR3/PPB2PP1/R1B3K1 w - - 5 18",
        "e3g3",
        "f4g3",
        "Peças em contato",
    ),
)
CASE_BY_ID = {case.id: case for case in CASES}


def play(case_id: str, uci: str) -> tuple[chess.Board, chess.Move]:
    board = CASE_BY_ID[case_id].board()
    move = chess.Move.from_uci(uci)
    if move not in board.legal_moves:
        raise ValueError("Illegal move in the specified position.")
    return board, move


def replay(board: chess.Board, moves: tuple[str, ...]) -> list[dict[str, str]]:
    position = board.copy()
    frames = []
    for uci in moves:
        move = position.parse_uci(uci)
        san = position.san(move)
        position.push(move)
        frames.append({"uci": uci, "san": san, "fen": position.fen()})
    return frames


def facts_for(board: chess.Board, move: chess.Move) -> str:
    return (
        f"captura={'sim' if board.is_capture(move) else 'não'}; "
        f"xeque={'sim' if board.gives_check(move) else 'não'}"
    )
