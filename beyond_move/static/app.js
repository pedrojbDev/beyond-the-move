import { Chessboard, COLOR, INPUT_EVENT_TYPE } from "./board/src/Chessboard.js";
import { Arrows, ARROW_TYPE } from "./board/src/extensions/arrows/Arrows.js";

const el = (id) => document.getElementById(id);
let exercises, current, move, line, step;
let generation = 0;
const board = new Chessboard(el("board"), {
  assetsUrl: "/static/board/assets/",
  style: { pieces: { file: "pieces/standard.svg" }, animationDuration: 120 },
  extensions: [{ class: Arrows }],
});

async function api(path, body) {
  const response = await fetch(path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : {});
  if (!response.ok) {
    throw new Error(response.status === 503 ? "Motor indisponível. Instale ou configure o Stockfish."
      : "Não foi possível completar a jogada. Confira o lance e tente novamente.");
  }
  return response.json();
}

function arrow(uci) {
  board.removeArrows();
  if (uci) board.addArrow(ARROW_TYPE.default, uci.slice(0, 2), uci.slice(2, 4));
}

function unlock() {
  el("ask").disabled = !move;
  el("reveal").disabled = !move;
}

function resetResults() {
  generation += 1;
  line = [];
  step = -1;
  el("steps").hidden = true;
  el("feedback").hidden = true;
  el("error").textContent = "";
  unlock();
}

async function selectMove(uci) {
  move = null;
  resetResults();
  const request = generation;
  try {
    const preview = await api("/api/preview", { case_id: current.id, move: uci });
    if (request !== generation) return;
    move = uci;
    board.disableMoveInput();
    board.setPosition(preview.fen, true);
    arrow(uci);
    el("move-readout").textContent = `Lance jogado: ${preview.san}`;
    unlock();
  } catch (error) {
    if (request === generation) el("error").textContent = error.message;
  }
}

async function selectExercise(listIndex) {
  current = exercises[listIndex];
  move = null;
  resetResults();
  arrow(null);
  el("reason").value = "";
  el("move-readout").textContent = "Escolha uma peça e faça um lance.";
  el("turn").textContent = current.turn === "white" ? "Brancas jogam" : "Pretas jogam";
  el("keyboard-move").replaceChildren(...current.moves.map((uci) => new Option(uci, uci)));
  el("keyboard-move").value = current.example_move;
  const color = current.turn === "white" ? COLOR.white : COLOR.black;
  board.disableMoveInput();
  await board.setOrientation(color);
  await board.setPosition(current.fen);
  board.enableMoveInput((event) => {
    if (event.type === INPUT_EVENT_TYPE.moveInputStarted) {
      return current.moves.some((legal) => legal.startsWith(event.squareFrom));
    }
    if (event.type === INPUT_EVENT_TYPE.validateMoveInput) {
      const candidate = event.squareFrom + event.squareTo;
      const legal = current.moves.find((uci) => uci === candidate || uci === candidate + "q");
      if (legal) {
        const exercise = current;
        window.setTimeout(() => { if (exercise === current) void selectMove(legal); }, 0);
      }
      return false;
    }
    return true;
  }, color);
}

function showStep() {
  const row = line[step];
  board.setPosition(row ? row.fen : current.fen, true);
  arrow(row ? row.uci : move);
  el("line").textContent = row ? `${step + 1}/${line.length} · ${row.san}` : "Posição inicial";
  el("prev").disabled = step < 0;
  el("next").disabled = step >= line.length - 1;
}

el("cases").addEventListener("change", (e) => void selectExercise(Number(e.target.value)));
el("example").addEventListener("click", () => void selectMove(current.example_move));
el("play").addEventListener("click", () => void selectMove(el("keyboard-move").value));
el("reset").addEventListener("click", () => void selectExercise(Number(el("cases").value)));
el("reason").addEventListener("input", () => {
  if (move) generation += 1;
  el("feedback").hidden = true;
  unlock();
});
el("coach").addEventListener("submit", async (event) => {
  event.preventDefault();
  const request = ++generation;
  el("ask").disabled = true;
  el("error").textContent = "";
  el("feedback").hidden = true;
  try {
    const result = await api("/api/hint", {
      case_id: current.id, move, reason: el("reason").value.trim(),
    });
    if (request !== generation) return;
    el("source").textContent = result.source === "adapter" ? "PISTA · MODELO AJUSTADO" : "PISTA · REGRAS";
    el("hint").textContent = result.hint;
    el("feedback").hidden = false;
  } catch (error) {
    if (request === generation) el("error").textContent = error.message;
  } finally {
    if (request === generation) unlock();
  }
});
el("reveal").addEventListener("click", async () => {
  const request = ++generation;
  el("reveal").disabled = true;
  el("error").textContent = "";
  try {
    const result = await api("/api/reveal", { case_id: current.id, move });
    if (request !== generation) return;
    line = result.line;
    step = -1;
    el("steps").hidden = false;
    showStep();
  } catch (error) {
    if (request === generation) el("error").textContent = error.message;
  } finally {
    if (request === generation) unlock();
  }
});
el("prev").addEventListener("click", () => { if (step >= 0) { step -= 1; showStep(); } });
el("next").addEventListener("click", () => { if (step + 1 < line.length) { step += 1; showStep(); } });

try {
  exercises = await api("/api/cases");
  for (const [index, item] of exercises.entries()) {
    el("cases").add(new Option(item.title, index));
  }
  await selectExercise(0);
  el("cases").disabled = false;
  el("example").disabled = false;
  el("keyboard-move").disabled = false;
  el("play").disabled = false;
  el("reset").disabled = false;
} catch (error) {
  el("turn").textContent = error.message;
}
