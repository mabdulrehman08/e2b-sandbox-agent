"""Run three real generate → execute → inspect → repair loops."""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from agent import Executor, Writer, solve
from tasks import TASKS


def main() -> int:
    load_dotenv(Path(__file__).with_name(".env"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=[task.name for task in TASKS], help="Run only one task")
    parser.add_argument("--max-attempts", type=int, default=3, choices=range(1, 6))
    parser.add_argument("--exercise-repair", action="store_true",
                        help="Start with a deliberate bug, then let the model repair it")
    args = parser.parse_args()
    missing = [key for key in ("E2B_API_KEY", "ANTHROPIC_API_KEY") if not os.environ.get(key)]
    if missing:
        print("Missing environment variables: " + ", ".join(missing) +
              ". Copy .env.example to .env and set your keys.", file=sys.stderr)
        return 2
    root = Path("runs") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-%fZ")
    print(f"Artifacts: {root}", flush=True)
    writer, executor = Writer(), Executor()
    results = []
    for task in TASKS:
        if args.task and task.name != args.task:
            continue
        print(task.name, flush=True)
        try:
            passed = solve(task, writer, executor, root / task.name,
                           args.max_attempts, args.exercise_repair)
        except Exception as error:
            # Avoid printing SDK request details which may contain credentials.
            print(f"  Infrastructure/model error: {type(error).__name__}. "
                  "Check credentials, quota and connectivity.", file=sys.stderr)
            passed = False
        print(f"  {'SOLVED' if passed else 'FAILED'}", flush=True)
        results.append(passed)
    print(f"Solved {sum(results)}/{len(results)} tasks. Artifacts: {root}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
