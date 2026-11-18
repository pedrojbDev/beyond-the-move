import argparse
import csv
import hashlib
import io
import json
import random
import re
from pathlib import Path
from urllib.parse import urlsplit

import chess
import zstandard

from .coaching import teaching_hint
from .domain import CASES, facts_for

SEED = 42
SIZES = {"train": 48, "validation": 8, "test": 12}
REASONS = {
    "train": {
        "troca": ("Queria trocar as damas para simplificar.", "Preferi ficar com menos peças."),
        "captura": ("Achei que a peça estava de graça.", "Minha ideia era ganhar material."),
        "ataque": ("Queria ameaçar o rei adversário.", "Pensei em criar uma ameaça de mate."),
        "defesa": ("Queria proteger minha peça atacada.", "Joguei para evitar uma ameaça."),
        "plano": ("Não pensei muito nesse lance.", "Foi só o primeiro lance que vi."),
    },
    "validation": {
        "troca": (
            "Ia forçar a troca de peças pesadas.",
            "Queria levar para um final mais simples.",
        ),
        "captura": ("Dava para pegar uma peça sem pagar.", "Vi uma chance de ficar no lucro."),
        "ataque": ("Minha ideia era perseguir o rei.", "O objetivo era deixar um mate no ar."),
        "defesa": ("Tentei salvar a peça em perigo.", "Quis neutralizar o ataque às minhas peças."),
        "plano": ("Só segui minha intuição.", "Não consigo explicar o que calculei."),
    },
    "test": {
        "troca": (
            "Se as duas rainhas saíssem, o resto ficaria mais fácil de jogar.",
            "A ideia era que cada lado entregasse uma peça e o jogo ficasse mais simples.",
            "Eu queria reduzir a confusão tirando uma peça pesada de cada lado.",
        ),
        "captura": (
            "Na hora eu achei que dava pra levar aquela peça sem perder nenhuma.",
            "Parece que o adversário deixou uma peça sobrando pra mim.",
            "Eu via uma peça dando sopa e queria sair no lucro.",
        ),
        "ataque": (
            "Quero encurralar o rei antes que ele consiga escapar.",
            "Minha intenção era deixar o rei deles sem saída.",
            "Tentei apertar o rei e forçar uma resposta.",
        ),
        "defesa": (
            "Eu precisava tirar minha peça da mira.",
            "Tentei apagar o incêndio do meu lado do tabuleiro.",
            "Quis botar a peça que estava em risco a salvo.",
        ),
        "plano": (
            "Pareceu natural, mas não tenho um motivo específico.",
            "Mexi meio no automático.",
            "Não tenho certeza do que eu queria com isso.",
        ),
    },
}


def game_id(url: str) -> str:
    parsed = urlsplit(url)
    match = re.fullmatch(r"/(?:game/)?([A-Za-z0-9]{8})(?:/(?:white|black))?", parsed.path)
    if parsed.hostname != "lichess.org" or match is None:
        raise ValueError("Unexpected Lichess game URL.")
    return match[1]


def read_positions(path: Path, limit: int = 450) -> list[dict[str, str]]:
    rows = []
    excluded = {case.id for case in CASES}
    boards = {" ".join(case.board().fen().split()[:4]) for case in CASES}
    with (
        path.open("rb") as compressed,
        zstandard.ZstdDecompressor().stream_reader(compressed) as stream,
        io.TextIOWrapper(stream, encoding="utf-8") as text,
    ):
        for record in csv.DictReader(text):
            if record["PuzzleId"] in excluded or not 950 <= int(record["Rating"]) <= 1750:
                continue
            position = chess.Board(record["FEN"])
            setup, solution, *_ = record["Moves"].split()
            position.push_uci(setup)
            key = " ".join(position.fen().split()[:4])
            if key in boards or not position.is_valid():
                continue
            candidates = sorted(
                (m for m in position.legal_moves if m.uci() != solution), key=lambda m: m.uci()
            )
            if not candidates:
                continue
            index = int.from_bytes(hashlib.sha256(key.encode()).digest()[:4]) % len(candidates)
            move = candidates[index]
            rows.append(
                {
                    "game": game_id(record["GameUrl"]),
                    "key": key,
                    "id": record["PuzzleId"],
                    "move": move.uci(),
                    "facts": facts_for(position, move),
                }
            )
            if len(rows) == limit:
                break
    return rows


def build_rows(source: list[dict], sizes: dict[str, int] = SIZES) -> dict[str, list[dict]]:
    rng = random.Random(SEED)
    order = list(source)
    rng.shuffle(order)
    keys, games = set(), set()
    distinct = []
    for row in order:
        if row["key"] in keys or row["game"] in games:
            continue
        keys.add(row["key"])
        games.add(row["game"])
        distinct.append(row)
    if len(distinct) < sum(sizes.values()):
        raise ValueError("Not enough disjoint source groups.")
    result = {}
    start = 0
    for split, size in sizes.items():
        result[split] = [
            {
                **row,
                "focus": label,
                "reason": rng.choice(variants),
                "hint": teaching_hint(label, row["facts"]),
            }
            for row in distinct[start : start + size]
            for label, variants in REASONS[split].items()
        ]
        start += size
    return result


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("archive", type=Path)
    cli.add_argument("sha256")
    cli.add_argument("--output", type=Path, default=Path("data/splits.json"))
    args = cli.parse_args()
    with args.archive.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    if digest != args.sha256:
        cli.error(f"Dataset checksum differs: {digest}")
    splits = build_rows(read_positions(args.archive))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"source_sha256": digest, "splits": splits}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print({key: len(value) for key, value in splits.items()})


if __name__ == "__main__":
    main()
