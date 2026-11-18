import { Chessboard, COLOR, INPUT_EVENT_TYPE } from "./board/src/Chessboard.js";
import { Arrows, ARROW_TYPE } from "./board/src/extensions/arrows/Arrows.js";

const el = (id) => document.getElementById(id);
const names = { p: "Peão", n: "Cavalo", b: "Bispo", r: "Torre", q: "Dama", k: "Rei" };
const sideName = (color) => color === "white" ? "brancas" : "pretas";
const board = new Chessboard(el("board"), {
  assetsUrl: "/static/board/assets/",
  style: { pieces: { file: "pieces/standard.svg" }, animationDuration: 120 },
  extensions: [{ class: Arrows }],
});
let cases = [], study = null, side = "white", history = [], view, selected = "";
let gameVersion = 0, questionVersion = 0, busy = true, asking = false;
let line = [], step = -1, candidate = null, lastMove = null;

async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(response.status === 503 ? "Motor indisponível. Confira o Stockfish."
      : "Não foi possível concluir. Confira a posição ou recomece a partida.");
  }
  return response.json();
}

function arrow(uci, danger = false) {
  board.removeArrows();
  if (uci) board.addArrow(danger ? ARROW_TYPE.danger : ARROW_TYPE.default,
    uci.slice(0, 2), uci.slice(2, 4));
}

function occupied(fen) {
  const pieces = new Map();
  for (const [rank, row] of fen.split(" ")[0].split("/").entries()) {
    let file = 0;
    for (const char of row) {
      if (char >= "1" && char <= "8") file += Number(char);
      else {
        const square = "abcdefgh"[file++] + (8 - rank);
        const name = names[char.toLowerCase()];
        const color = char === char.toLowerCase() ? "⚫" : "⚪";
        pieces.set(square, `${color} ${name} · ${square}`);
      }
    }
  }
  return pieces;
}

function updateControls() {
  const moves = !busy && view && view.turn === side && !view.outcome ? view.moves : [];
  el("keyboard-move").disabled = moves.length === 0;
  el("play").disabled = moves.length === 0;
  el("ask").disabled = busy || asking || !selected;
  el("piece").disabled = busy || !view;
  el("fetch-bot").hidden = !!study || busy || !view || view.turn === side || !!view.outcome;
  el("reveal").disabled = busy || !candidate;
  el("example").disabled = busy;
}

function invalidateAdvice(clearArrow = true) {
  questionVersion += 1;
  asking = false;
  el("feedback").hidden = true;
  el("error").textContent = "";
  if (clearArrow) arrow(lastMove);
  updateControls();
}

function setPiece(square) {
  if (!view || !occupied(view.fen).has(square)) return;
  if (selected !== square) {
    selected = square;
    invalidateAdvice();
  }
  el("piece").value = selected;
}

function render(frame, activeHistory, uci, animate = true) {
  view = frame;
  history = [...activeHistory];
  lastMove = uci;
  const pieces = occupied(view.fen);
  if (!pieces.has(selected)) selected = "";
  el("piece").replaceChildren(new Option("Selecione uma peça", ""),
    ...Array.from(pieces, ([square, name]) => new Option(name, square)));
  el("piece").value = selected;
  el("keyboard-move").replaceChildren(...view.moves.map((move) => new Option(move, move)));
  el("turn").textContent = frame.outcome
    ? (frame.winner ? `Fim de partida · Vitória das ${sideName(frame.winner)}` : "Fim de partida · Empate")
    : `${frame.turn === side ? "Sua vez" : study ? "Vez do adversário" : busy ? "Bot pensando…" : "Vez do bot"} · ${sideName(frame.turn)}${frame.check ? " · Xeque" : ""}`;
  board.setPosition(view.fen, animate);
  invalidateAdvice();
  updateInput();
}

function updateInput() {
  board.disableMoveInput();
  if (busy || !view || view.turn !== side || view.outcome || (study && candidate)) return;
  board.enableMoveInput((event) => {
    if (event.type === INPUT_EVENT_TYPE.moveInputStarted) {
      setPiece(event.squareFrom);
      return view.moves.some((uci) => uci.startsWith(event.squareFrom));
    }
    if (event.type === INPUT_EVENT_TYPE.validateMoveInput) {
      const fromTo = event.squareFrom + event.squareTo;
      const move = view.moves.find((uci) => uci === fromTo || uci === fromTo + "q");
      const version = gameVersion;
      if (move) setTimeout(() => { if (version === gameVersion) void play(move); }, 0);
      return false;
    }
    return true;
  }, side === "white" ? COLOR.white : COLOR.black);
}

function frameFromStudy(fen, moves = []) {
  return { fen, turn: fen.split(" ")[1] === "w" ? "white" : "black", moves };
}

async function callBot(version) {
  if (study || !view || view.outcome || view.turn === side) return;
  busy = true;
  updateControls();
  updateInput();
  el("turn").textContent = "Bot pensando…";
  try {
    const reply = await api("/api/bot", { history, side });
    if (version !== gameVersion) return;
    busy = false;
    el("move-readout").textContent = `Bot jogou ${reply.san}.`;
    render(reply, [...history, reply.move], reply.move);
  } catch (error) {
    if (version === gameVersion) {
      busy = false;
      el("turn").textContent = "Vez do bot";
      el("error").textContent = error.message;
      updateControls();
    }
  }
}

async function reset() {
  const version = ++gameVersion;
  study = cases.find(({ id }) => id === el("cases").value) ?? null;
  side = study?.turn ?? el("side").value;
  view = null;
  lastMove = null;
  history = [];
  selected = "";
  line = [];
  step = -1;
  candidate = null;
  busy = true;
  el("reason").value = "";
  el("replay").hidden = !study;
  el("steps").hidden = true;
  el("example").hidden = !study;
  el("side-control").hidden = !!study;
  el("move-readout").textContent = "";
  el("turn").textContent = "Preparando posição…";
  invalidateAdvice();
  updateInput();
  try {
    const frame = study ? frameFromStudy(study.fen, study.moves) : await api("/api/game", {});
    if (version !== gameVersion) return;
    await board.setOrientation(side === "white" ? COLOR.white : COLOR.black);
    if (version !== gameVersion) return;
    busy = false;
    render(frame, [], null, false);
    if (!study && frame.turn !== side) await callBot(version);
  } catch (error) {
    if (version === gameVersion) {
      busy = false;
      el("turn").textContent = "Não foi possível iniciar.";
      el("error").textContent = error.message;
    }
  }
}

async function play(move) {
  if (busy || !view.moves.includes(move)) return;
  const version = ++gameVersion;
  busy = true;
  invalidateAdvice();
  updateInput();
  try {
    if (study) {
      const payload = await api("/api/preview", { case_id: study.id, move });
      if (version !== gameVersion) return;
      candidate = move;
      busy = false;
      selected = move.slice(2, 4);
      el("move-readout").textContent = `Você jogou ${payload.san}.`;
      render(frameFromStudy(payload.fen), [move], move);
      return;
    }
    const moves = [...history, move];
    const frame = await api("/api/game", { history: moves });
    if (version !== gameVersion) return;
    selected = move.slice(2, 4);
    busy = false;
    render(frame, moves, move);
    await callBot(version);
  } catch (error) {
    if (version === gameVersion) {
      busy = false;
      el("error").textContent = error.message;
      updateControls();
      updateInput();
    }
  }
}

function showStep() {
  const frame = line[step];
  const active = line.slice(0, step + 1).map((value) => value.uci);
  render(frame ? frameFromStudy(frame.fen) : frameFromStudy(study.fen), active, frame?.uci);
  el("line").textContent = frame ? `${step + 1}/${line.length} · ${frame.san}` : "Posição inicial";
  el("prev").disabled = step < 0;
  el("next").disabled = step >= line.length - 1;
}

el("board").addEventListener("click", (event) => {
  const square = event.target.closest("[data-square]")?.dataset.square;
  if (!busy && square) setPiece(square);
});
el("piece").addEventListener("change", (event) => {
  selected = event.target.value;
  invalidateAdvice();
});
el("cases").addEventListener("change", () => void reset());
el("side").addEventListener("change", () => void reset());
el("reset").addEventListener("click", () => void reset());
el("example").addEventListener("click", () => void play(study.example_move));
el("play").addEventListener("click", () => void play(el("keyboard-move").value));
el("fetch-bot").addEventListener("click", () => void callBot(gameVersion));
el("reason").addEventListener("input", () => invalidateAdvice());
el("coach").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selected || busy) return;
  invalidateAdvice();
  const request = questionVersion;
  asking = true;
  updateControls();
  try {
    const result = await api("/api/advice", {
      case_id: study?.id ?? null, side, history, square: selected, question: el("reason").value.trim(),
    });
    if (request !== questionVersion || result.fen !== view.fen) return;
    el("source").textContent = result.source === "stockfish" ? "TREINADOR · STOCKFISH" : "TREINADOR · TABULEIRO";
    el("hint").textContent = result.answer;
    el("why").textContent = result.why;
    el("feedback").hidden = false;
    arrow(result.move?.uci ?? result.threat?.uci, !!result.threat);
  } catch (error) {
    if (request === questionVersion) el("error").textContent = error.message;
  } finally {
    if (request === questionVersion) { asking = false; updateControls(); }
  }
});
el("reveal").addEventListener("click", async () => {
  const version = gameVersion;
  el("reveal").disabled = true;
  try {
    const result = await api("/api/reveal", { case_id: study.id, move: candidate });
    if (version !== gameVersion) return;
    line = result.line;
    step = 0;
    el("steps").hidden = false;
    showStep();
  } catch (error) {
    if (version === gameVersion) el("error").textContent = error.message;
  } finally {
    if (version === gameVersion) updateControls();
  }
});
el("prev").addEventListener("click", () => { if (step >= 0) { step -= 1; showStep(); } });
el("next").addEventListener("click", () => { if (step + 1 < line.length) { step += 1; showStep(); } });

try {
  cases = await api("/api/cases");
  for (const item of cases) el("cases").add(new Option(`Treino · ${item.title}`, item.id));
  el("cases").disabled = false;
  el("reset").disabled = false;
  await reset();
} catch (error) {
  el("turn").textContent = error.message;
}
