"""Compare simple PT-BR routing and an unchanged local Qwen on a small audit."""

import json
from pathlib import Path

from beyond_move.piece_coach import question_focus
from beyond_move.training import open_model

QUESTIONS = (
    ("O que eu faço com esse bispo agora?", "plan"),
    ("Vale a pena desenvolver meu cavalo?", "plan"),
    ("Qual seria um bom plano pra torre?", "plan"),
    ("Que ideia você sugere para a dama?", "plan"),
    ("Meu bispo está ameaçado?", "safety"),
    ("Quem protege esse peão?", "safety"),
    ("Minha torre ficou pendurada?", "safety"),
    ("Tem risco de perder o cavalo?", "safety"),
    ("Em quais casas o cavalo pode jogar?", "mobility"),
    ("Quais lances são legais para o bispo?", "mobility"),
    ("Onde posso mover essa torre?", "mobility"),
    ("Quantas opções tenho com a dama?", "mobility"),
)

PROMPT = (
    "Classifique perguntas de xadrez em português. plan = pedir plano ou conselho; "
    "safety = perguntar por ameaça, risco ou defesa; mobility = pedir casas ou lances legais. "
    "Responda apenas com uma destas três palavras: plan, safety, mobility."
)


def main():
    import torch

    model, tokenizer = open_model(Path(".local/base"))
    model.eval()
    rows = []
    for text, expected in QUESTIONS:
        prompt = tokenizer.apply_chat_template(
            [{"role": "system", "content": PROMPT}, {"role": "user", "content": text}],
            tokenize=False,
            add_generation_prompt=True,
        )
        batch = tokenizer(prompt, return_tensors="pt")
        with torch.inference_mode():
            output = model.generate(
                **batch,
                max_new_tokens=10,
                do_sample=False,
                temperature=None,
                top_p=None,
                top_k=None,
            )
        raw = tokenizer.decode(output[0, batch.input_ids.shape[1] :], skip_special_tokens=True)
        rows.append(
            {
                "question": text,
                "expected": expected,
                "rules": question_focus(text),
                "base": raw.strip().lower(),
            }
        )
    scores = {key: sum(row[key] == row["expected"] for row in rows) for key in ("rules", "base")}
    print(json.dumps({"rows": rows, "correct": scores}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
