import re
import unicodedata

HINTS = {
    "troca": "Se o adversário aceitar a troca, o que muda nas peças que continuam no tabuleiro?",
    "captura": "Antes de contar o material, que peça adversária poderia recapturar?",
    "ataque": "Se o adversário responder com um lance forçado, sua ameaça ainda funciona?",
    "defesa": "O lance cobre a ameaça imediata ou só protege uma das peças atacadas?",
    "plano": "Qual seria a resposta mais incômoda do adversário a essa ideia?",
}
KEYWORDS = {
    "troca": ("troc", "simplif", "sem damas", "sem rainhas"),
    "captura": ("captur", "de graca", "ganhar material", "comer", "desprotegid"),
    "ataque": ("atac", "ameaç", "ameac", "mate", "dar xeque"),
    "defesa": ("defend", "prote", "segur", "evitar", "salvar"),
}


def focus_for(reason: str) -> str:
    text = unicodedata.normalize("NFKD", reason.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return next(
        (label for label, terms in KEYWORDS.items() if any(word in text for word in terms)),
        "plano",
    )


def fallback(reason: str) -> dict[str, str]:
    focus = focus_for(reason)
    return {"focus": focus, "hint": HINTS[focus], "source": "rules"}


def parse_hint(text: str) -> tuple[str, str] | None:
    label, divider, hint = text.strip().partition("|")
    hint = hint.strip()
    if not divider or label.strip() not in HINTS or not 18 <= len(hint) <= 220:
        return None
    if "\n" in hint or "|" in hint or not hint.endswith("?") or has_notation(hint):
        return None
    return label.strip(), hint


def has_notation(text: str) -> bool:
    return bool(re.search(r"(?i)(?:[a-h][1-8])|(?:[O0][-–][O0])", text))


def teaching_hint(label: str, facts: str) -> str:
    if label == "captura" and "recaptura=sim" in facts:
        return "Se o adversário recapturar sua peça, você ainda sai ganhando material?"
    if label == "ataque" and "xeque=sim" in facts:
        return "Antes de continuar o ataque, de quantas maneiras o rei pode sair do xeque?"
    return HINTS[label]
