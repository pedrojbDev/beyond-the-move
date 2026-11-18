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

EXTRA_TRAIN_REASONS = {
    "troca": (
        "Se a gente trocar as damas, o jogo fica menos complicado.",
        "Quero jogar um final com poucas peças.",
        "Minha ideia era ficar sem as duas torres.",
        "Tirei as peças mais fortes dos dois lados.",
        "Queria que cada um ficasse com uma peça a menos.",
        "Com as rainhas fora, fica mais tranquilo.",
        "Era para simplificar, não para ganhar material.",
        "Meu plano era reduzir a quantidade de peças.",
        "Preferi uma posição mais simples sem a dama deles e a minha.",
        "Deixo ele tomar a minha e dou a dele em troca.",
        "Estou na frente e queria chegar logo no final.",
        "Pensei que uma troca equilibrada ajudava meu final.",
    ),
    "captura": (
        "Essa peça ficou solta, pensei em pegar.",
        "Queria levar o bispo sem dar nada em troca.",
        "Pareceu que ninguém defendia o cavalo.",
        "Eu conto uma peça grátis aqui.",
        "Achei que ele não podia tomar de volta.",
        "Fui atrás da torre que ele largou.",
        "Quero sair dessa jogada com uma peça a mais.",
        "A peça ficou pendurada, por isso eu comi.",
        "Não vi de onde poderia vir a recaptura.",
        "Tentei aproveitar o peão que ficou sozinho.",
        "Quis ficar com mais material do que ele.",
        "Não achei que perderia nada se pegasse o bispo.",
    ),
    "ataque": (
        "Quero apertar o rei adversário.",
        "Tentei deixar o rei deles preso.",
        "Pensei que o rei deles não teria espaço.",
        "Quero forçar a defesa do rei.",
        "A ideia é tirar as casas de fuga do rei.",
        "Meu objetivo era colocar o outro rei em perigo.",
        "Preferi perseguir o rei com as peças pesadas.",
        "Quero fazer as pretas responderem a uma ameaça.",
        "Joguei preparando um ataque direto.",
        "Pensei em deixar o mate ameaçado.",
        "Queria dar xeques seguidos até chegar perto do rei.",
        "O foco era atacar, mesmo sem capturar nada.",
    ),
    "defesa": (
        "Meu cavalo estava pendurado e eu queria segurar.",
        "Quis deixar minha torre fora de perigo.",
        "Estava tentando bloquear a ameaça na minha ala.",
        "Preferi tirar a peça atacada dali.",
        "Tentei proteger meu rei primeiro.",
        "Fiz isso para ele não pegar meu bispo.",
        "Quero manter meu peão a salvo.",
        "Joguei mais atrás para não perder material.",
        "Eu estava sob ataque e resolvi recuar.",
        "Minha ideia era evitar o xeque que eu estava vendo.",
        "Pus uma peça para cobrir a outra que ele estava olhando.",
        "Achei que precisava salvar minha peça antes de atacar.",
    ),
    "plano": (
        "Foi na intuição, não calculei nenhuma resposta.",
        "Só movi a peça, sem objetivo claro.",
        "Não tive um plano para esse lance.",
        "Eu chutaria essa jogada, não sei justificar.",
        "Fiquei sem saber o que fazer e joguei.",
        "Não cheguei a olhar o que vinha depois.",
        "Foi no reflexo.",
        "Não sei bem o que eu estava tentando.",
        "Eu fiz por hábito.",
        "Não vi uma ideia específica.",
        "Me pareceu um lance normal e só.",
        "Mexi a peça sem montar estratégia.",
    ),
}


def augment_training(splits: dict[str, list[dict]]) -> dict[str, list[dict]]:
    rng = random.Random(2718)
    return {
        **splits,
        "train": splits["train"]
        + [
            {**row, "reason": reason}
            for row in splits["train"]
            for reason in rng.sample(EXTRA_TRAIN_REASONS[row["focus"]], 3)
        ],
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
    cli.add_argument("--augment-train", action="store_true")
    args = cli.parse_args()
    with args.archive.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    if digest != args.sha256:
        cli.error(f"Dataset checksum differs: {digest}")
    splits = build_rows(read_positions(args.archive))
    if args.augment_train:
        splits = augment_training(splits)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"source_sha256": digest, "splits": splits}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print({key: len(value) for key, value in splits.items()})


if __name__ == "__main__":
    main()
