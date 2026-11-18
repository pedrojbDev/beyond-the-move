---
license: apache-2.0
language:
- pt
base_model: Qwen/Qwen2.5-0.5B-Instruct
pipeline_tag: text-generation
library_name: peft
tags:
- chess
- lora
- education
---

# Beyond the Move / Além do Lance

A rank-8 LoRA adapter fine-tuned on CPU for a Brazilian Portuguese chess practice
experiment. Use it with `Qwen/Qwen2.5-0.5B-Instruct` at revision
`7ae557604adf67be50417f59c2c2f167def9a775`. The base weights are not bundled.

The adapter proposes a coaching focus and a short question given a natural-language
rationale and three board flags. It is not a chess engine and receives no
solution line. See the [project](https://github.com/pedrojbDev/beyond-the-move)
for the exact prompt, notation guard, UI and reproduction commands.

## Training and results

Chess positions: [Lichess puzzle export](https://database.lichess.org/#puzzles),
CC0 1.0. Coaching rationale and target pairs are original synthetic examples.
48/8/12 source position groups for training/validation/test with disjoint
phrasing pools. One of two trials selected on validation; test run once.
540,672 LoRA parameters, 180 CPU steps, seed 42 and about 434 seconds.

| On the 60 synthetic held-out examples | Focus accuracy | Macro F1 | Invalid output |
|---|---:|---:|---:|
| Base under the same prompt | 0/60 | 0.000 | 60/60 |
| Keyword rules | 12/60 | 0.067 | 0/60 |
| LoRA adapter | 31/60 | 0.483 | 0/60 |

Strict five-intent group accuracy was 0/12. The adapter frequently confused
defense with attack and capture with a trade. Explicit move notation was
not observed in this small test; hidden spoilers, factual errors, prompt
adherence and usefulness on real learner language are not guaranteed.
The base result includes format failures on one prompt. This is a small
instruction-following experiment, not an Elo or teaching-effectiveness result.

`metrics.json` contains the confusion counts. `training-manifest.json` pins the
data, training code and artifact digest. Weights use safetensors.
