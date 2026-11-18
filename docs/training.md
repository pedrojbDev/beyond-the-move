# Training and evaluation

The reference source was the [Lichess CC0 puzzle export](https://database.lichess.org/#puzzles)
dated 2026-11-11 (SHA-256 `7b0d235fa40cfd7fdb7df1fec56a96b3b6ee1496b32ed2eb05be90d0ebf94253`).
The URL is mutable, so `fixtures/position-sample.json` preserves the ordered 450
derived positions from that reference, not the full archive. The exact sampled
rows can be rebuilt with `beyond_move.data` from the original archive when available.
A puzzle's setup move is applied before the position is used.

From the repository root, after the installation described in the README:

```sh
sample=fixtures/position-sample.json
digest=a975da04ce486f52dfe261a2b79e5ac6d874cdc557de23ec5af8534bedc9c509
uv run --locked --extra model python -m beyond_move.data "$sample" "$digest" \
  --position-sample --augment-train --output data/augmented.json
sha256sum data/augmented.json
OMP_NUM_THREADS=2 uv run --locked --extra model python -m beyond_move.training fit \
  --steps 180 --data data/augmented.json --output artifacts/reproduction
OMP_NUM_THREADS=2 uv run --locked --extra model python -m beyond_move.training evaluate \
  --split test --data data/augmented.json --output artifacts/reproduction
```

The reproduced split SHA-256 should be
`afa3da41dc030b5be7785816e4c898b8a1683c4224d087bdb43f89d15aa54c08`.
Different CPU/library versions can change trained bytes and scores. The manifest
in `model/` documents the actual training revision rather than the release SHA.

Groups are unique by source game and first four fields of canonical FEN. There
are 48/8/12 train/validation/test groups and five coaching intents in each group.
Different rationales on the same candidate are synthetic, and the three splits
have disjoint phrasing pools. Ground-truth focus labels are authored, not player
annotations. Trial 2 augmented only the training phrases (960 total rows,
180 sampled optimizer steps); validation and test rows remained unchanged.
Trial 1's validation macro F1 was 0.185; trial 2 scored 0.784 and was selected
before executing the held-out test once. The final training took 434.21 seconds
on two CPU threads; process peak RSS was 3,262,752 KiB. See `model/metrics.json`
for the held-out confusion counts and `docs/test-audit.json` for raw completions.
Only the fixed template task and explicit notation rates are scored
automatically; a short text review found systematic focus mistakes, not a
validated guarantee that a question is accurate, helpful or spoiler-free.

## Historical browser smoke

The instructions below are for the `v1.0.0` tag and its archived rationale-hint
UI and browser script. The current UI is covered in [Position-aware coaching](piece-coach.md).
With Firefox, Node.js and the historical app running with `COACH_ADAPTER_PATH=model`:

```sh
npm install --prefix .local/tools puppeteer-core@24.12.1
node tests/browser.mjs
```

The script drives a board click, verifies two actual adapter responses, steps
through the first engine reply, checks a 390 px viewport and saves screenshots.
In the constrained sandbox the process was limited to two CPU affinities to
keep Firefox below the thread limit.
