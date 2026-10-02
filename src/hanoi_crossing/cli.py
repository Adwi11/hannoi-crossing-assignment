"""Play Hanoi Crossing from the command line: random games or recorded replays."""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from .engine import ACTIONS, Action, CurrentState, Observation, Player, TurnResult

# Picks the next move from what its player can see on the board.
ChooseMove = Callable[[Observation], Action]

# TurnResult does not record who moved, so the game loop keeps the (player, result) pair.
Step = tuple[Player, TurnResult]


def random_moves(rng: random.Random) -> ChooseMove:
    return lambda obs: rng.choice([a for a in ACTIONS if obs.check_state(a) is None])


def scripted_moves(moves: Iterable[Action]) -> ChooseMove:
    remaining = iter(moves)
    return lambda obs: next(remaining, Action.skip())  # skips once the recorded moves run out


def play(
    state: CurrentState, turn_order: Iterable[Player], choosers: Mapping[Player, ChooseMove], max_steps: int | None = None
) -> tuple[CurrentState, list[Step]]:
    steps = []
    for player in turn_order:
        if state.over or len(steps) == max_steps:
            break
        result = state.nextStep(player, choosers[player](state.observe(player)))
        steps.append((player, result))
        state = result.state
    return state, steps


def random_game(n: int, seed: int, max_steps: int | None = None) -> tuple[CurrentState, list[Step]]:
    rng = random.Random(seed)  
    turns = (rng.choice((Player.A, Player.B)) for _ in itertools.count())
    return play(CurrentState.new(n), turns, {p: random_moves(rng) for p in Player}, max_steps)


def replay_game(data: Any) -> tuple[CurrentState, list[Step], dict[Player, list[Action]]]:
    """Validate a replay dict {n, turn_order, moves} and play each player's recorded moves."""
    if not isinstance(data, Mapping):
        raise ValueError("replay must be a JSON object")
    # Unknown keys are errors: a typo like "turnorder" must not silently replay an empty game.
    if unknown := set(data) - {"n", "turn_order", "moves"}:
        raise ValueError(f"unknown replay keys: {sorted(unknown)}")
    order, raw_moves = data.get("turn_order"), data.get("moves", {})
    if not isinstance(order, (str, list)) or not all(p in ("A", "B") for p in order):
        raise ValueError("turn_order must be a string like 'ABBA' or a list like ['A', 'B']")
    if not isinstance(raw_moves, Mapping) or not set(raw_moves) <= {"A", "B"}:
        raise ValueError("moves must map 'A' and/or 'B' to a list of actions")
    if not all(
        isinstance(seq, list) and all(isinstance(a, Mapping) and "type" in a for a in seq)
        for seq in raw_moves.values()
    ):
        raise ValueError('each move must be an object like {"type": "lift", "pole": 1}')
    moves = {p: [Action.from_dict(a) for a in raw_moves.get(p.value, [])] for p in Player}
    final, steps = play(CurrentState.new(data.get("n")), map(Player, order), {p: scripted_moves(moves[p]) for p in Player})
    return final, steps, moves


def record(n: int, steps: list[Step]) -> dict[str, Any]:
    """A replay dict that reproduces these steps exactly."""
    return {
        "n": n,
        "turn_order": "".join(player.value for player, _ in steps),
        "moves": {p.value: [s.action.to_dict() for player, s in steps if player is p] for p in Player},
    }


def summary(final: CurrentState, steps: list[Step], max_steps: int | None = None, trace: bool = False) -> dict[str, Any]:
    stop = "won" if final.over else "max_steps" if len(steps) == max_steps else "turn_order_exhausted"
    out = {
        "winner": final.winner.value if final.winner else None,
        "stop_reason": stop,
        "turns_played": len(steps),
        "illegal_actions": {p.value: sum(player is p and not s.legal() for player, s in steps) for p in Player},
        "final_state": final.to_dict(),
    }
    if trace:
        out["trace"] = [
            {"turn": s.state.turn, "player": player.value, "action": s.action.to_dict(),
             "legal": s.legal(), "reason": s.reason.value if s.reason else None}
            for player, s in steps
        ]
    return out


def to_text(payload: dict[str, Any]) -> str:
    illegal, state = payload["illegal_actions"], payload["final_state"]
    lines = [
        f"winner: {payload['winner'] or '-'}   stop: {payload['stop_reason']}   "
        f"turns: {payload['turns_played']}   illegal: A={illegal['A']} B={illegal['B']}"
    ]
    lines += [f"{key}: {payload[key]}" for key in ("seed", "unused_moves") if key in payload]
    for step in payload.get("trace", []):
        action = " ".join(str(v) for v in step["action"].values() if v is not None)
        mark = "" if step["legal"] else f"   ILLEGAL ({step['reason']})"
        lines.append(f"  {step['turn']:>5}. {step['player']} {action}{mark}")
    lines += [f"  {label:<3}| {' '.join(map(str, disks)) or '-'}" for label, disks in state["poles"].items()]
    lines.append("  " + "   ".join(f"hand {p}: {d or '-'}" for p, d in state["hands"].items()))
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "replay":
        data = json.loads(sys.stdin.read() if args.file == "-" else Path(args.file).read_text())
        final, steps, moves = replay_game(data)
        out = summary(final, steps, trace=args.trace)
        # Moves left over after the game ended usually mean the recording and turn order disagree.
        out["unused_moves"] = {p.value: max(0, len(moves[p]) - sum(player is p for player, _ in steps)) for p in Player}
        return out

    # Always report the seed, even when the user didn't pick one, so any run can be reproduced.
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(2**32)
    final, steps = random_game(args.n, seed, args.max_steps)
    return {"seed": seed, **summary(final, steps, args.max_steps, args.trace)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hanoi-crossing", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    rep = sub.add_parser("replay", help="replay recorded moves and print the final state")
    rep.add_argument("file", help="replay JSON file, or '-' for stdin")

    rnd = sub.add_parser("random", help="two random players play each other")
    rnd.add_argument("-n", type=int, default=3, help="disks per player (default: 3)")
    rnd.add_argument("--seed", type=int, help="RNG seed (default: random, printed in the output)")
    rnd.add_argument("--max-steps", type=int, default=100_000, help="stop after this many steps")

    for cmd in (rep, rnd):
        cmd.add_argument("--format", choices=("json", "text"), default="json", help="output format (default: json)")
        cmd.add_argument("--trace", action="store_true", help="include every step in the output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = run(args)
    except (ValueError, OSError) as exc:  # JSONDecodeError is a ValueError
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(to_text(payload) if args.format == "text" else json.dumps(payload, indent=2))
    return 0
