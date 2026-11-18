# Attribution and licensing

- Application source: GPL-3.0-or-later; see `LICENSE`. The application uses
  [python-chess](https://github.com/niklasf/python-chess) (GPL-3.0-or-later).
- [Stockfish 17.1](https://github.com/official-stockfish/Stockfish/tree/sf_17.1)
  (GPL-3.0) runs as a separate UCI executable. It is fetched from the official
  release; this repository does not redistribute the binary.
- [cm-chessboard 8.11.0](https://github.com/shaack/cm-chessboard/tree/v8.11.0)
  JavaScript, CSS and arrow assets: MIT license, copyright Stefan Haack, preserved
  at `beyond_move/static/board/LICENSE`. Copied unmodified from the npm package.
- The `standard.svg` sprite is explicitly **CC BY-SA 3.0**, not MIT; attribution
  and authors are embedded in that unchanged file. Original
  [Wikimedia standard pieces](https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces/Standard);
  [license](https://creativecommons.org/licenses/by-sa/3.0/). The boards depicted
  in the demo screenshots contain those pieces; the screenshots are offered
  under CC BY-SA 3.0 as well. The noncommercial Staunty set is not included.
- [Lichess open puzzle data](https://database.lichess.org/#puzzles): CC0 1.0.
  The frozen sample is a transformed, small subset (FEN, game/puzzle identifier,
  candidate, and board facts); no full downloaded file or usernames are shipped.
  Original synthetic rationales and coaching targets in `beyond_move/data.py`
  and `beyond_move/coaching.py` are additionally available under CC0 1.0 as data.
- Qwen base model and the distributed LoRA weights: Apache-2.0; see `model/LICENSE`.
  Base weights are fetched from Qwen, never rehosted in this project.
