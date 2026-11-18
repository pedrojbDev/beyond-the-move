from beyond_move.coaching import parse_hint


def test_game_identification_supports_current_and_legacy_lichess_urls():
    from beyond_move.data import game_id

    assert game_id("https://lichess.org/game/787zsVup/black#48") == "787zsVup"
    assert game_id("https://lichess.org/787zsVup#48") == "787zsVup"


def test_coach_output_rejects_explicit_solutions_and_bad_formats():
    assert parse_hint("captura|Que peça poderia recapturar depois desse lance?")[0] == "captura"
    assert parse_hint("captura|E se as pretas jogarem Dxe4 nessa posição?") is None
    assert parse_hint("defesa|Antes disso, você poderia escolher O-O?") is None
    assert parse_hint("plano|Qual é a próxima ameaça?\nOutro texto.") is None


def test_split_is_deterministic_and_groups_game_position_and_reason():
    from beyond_move.data import build_rows

    source = [
        {"game": f"game-{i}", "key": f"position-{i}", "facts": "captura=não; xeque=não"}
        for i in range(12)
    ]
    source.append({**source[0], "game": "duplicate-game"})
    first = build_rows(source, {"train": 5, "validation": 2, "test": 2})
    assert first == build_rows(source, {"train": 5, "validation": 2, "test": 2})
    seen = {}
    for rows in first.values():
        assert len({row["focus"] for row in rows}) == 5
        for field in ("game", "key", "reason"):
            items = {row[field] for row in rows}
            assert not items & seen.setdefault(field, set())
            seen[field] |= items


def test_pair_metric_requires_correct_labels_on_both_reasons():
    from beyond_move.evaluate import score

    rows = [{"key": "a", "focus": "troca"}, {"key": "a", "focus": "captura"}]
    assert score(rows, ["troca", "troca"])["pair_accuracy"] == 0
    assert score(rows, ["troca", "captura"])["pair_accuracy"] == 1
    assert score(rows, [None, "captura"])["invalid_rate"] == 0.5
