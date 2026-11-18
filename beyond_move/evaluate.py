from collections import Counter, defaultdict

from .coaching import HINTS


def score(rows: list[dict], predictions: list[str | None]) -> dict:
    if not rows or len(rows) != len(predictions):
        raise ValueError("Require one prediction per input row.")
    pairs = defaultdict(list)
    confusion = {label: Counter() for label in HINTS}
    for row, guess in zip(rows, predictions, strict=True):
        confusion[row["focus"]][guess or "invalid"] += 1
        pairs[row["key"]].append(guess == row["focus"])
    f1s = []
    for label, counts in confusion.items():
        support = counts.total()
        if support:
            predicted = sum(c[label] for c in confusion.values())
            f1s.append(2 * counts[label] / (support + predicted))
    return {
        "accuracy": sum(map(sum, pairs.values())) / len(rows),
        "macro_f1": sum(f1s) / len(f1s),
        "pair_accuracy": sum(all(values) for values in pairs.values()) / len(pairs),
        "invalid_rate": predictions.count(None) / len(rows),
        "confusion": {label: dict(counts) for label, counts in confusion.items()},
    }
