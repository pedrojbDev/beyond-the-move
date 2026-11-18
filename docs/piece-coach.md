# Position-aware coaching

The previous UI mapped a learner rationale into one of five hint categories.
It only saw two or three move flags and couldn't advise about a particular
piece or replay frame. That endpoint and its historical weights are kept
for reproducibility; the default UI uses the new advice endpoint.

The client sends the visible frame's move history, player color, selected
square and question. The server rejects arbitrary boards and replays standard
chess or an allowlisted exercise. A response carries its FEN so the UI won't
show an old result over a different frame. No user history is stored server-side.

Only one move can be applied per turn in the UI. The bot picks one legal reply
using a small deterministic material heuristic; this is not an Elo model.
Mouse/touch promotion defaults to a queen; the keyboard picker offers the
other legal promotions. The app exposes three question families: what to do,
where the piece can move, and whether its square is attacked. Safety counts
include geometric attacks, including pinned attackers; they do not prove that
a capture wins material. When it is the opponent's turn, the coach can flag
a legal capture but cannot recommend a move for the learner. On the learner's
turn, Stockfish ranks that piece's legal moves with time and node limits.

## Routing audit

`OMP_NUM_THREADS=2 uv run --locked --extra model python -m scripts.compare_routing`
compares the fixed heuristics with unchanged Qwen2.5-0.5B-Instruct on twelve
author-written PT-BR questions spanning the supported families. Use the base
files downloaded by `scripts.fetch_assets`. The [recorded result](coach-routing-audit.json)
was 11/12 for rules and 6/12 for the base. This tiny audit measures exact intent
labels, not answer quality or realistic generalization. The missed example
“Tem risco de perder o cavalo?” went to the default plan. No new training or
unverified model-generated chess claims were added.

## Browser smoke

Run the app with Stockfish, then use Firefox and Node:

```sh
npm install --prefix .local/tools puppeteer-core@24.12.1
DEMO_URL=http://127.0.0.1:8765/ node tests/browser.mjs
```

The smoke test clicks a bishop, plays a legal move, waits for a bot reply,
chooses Black, reproduces `Bf5 Qxe5` and verifies changed advice at the next
frame. It also checks the layout at 390 px and captures the screenshots.
