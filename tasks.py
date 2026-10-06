"""Small, explicit contracts; expected answers stay on the host."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Task:
    name: str
    prompt: str
    cases: tuple[tuple[Any, Any], ...]
    buggy: str


TASKS = (
    Task(
        "merge-intervals",
        "Merge overlapping or touching closed integer intervals. Return sorted intervals. "
        "Input is a JSON list of [start,end] pairs with start <= end; empty input is valid.",
        (([[5, 7], [1, 3], [3, 6]], [[1, 7]]), ([], []),
         ([[1, 10], [2, 3], [12, 12]], [[1, 10], [12, 12]]),
         ([[-5, -2], [-2, 0], [4, 6]], [[-5, 0], [4, 6]])),
        "import json, sys\nprint(json.dumps(sorted(json.load(sys.stdin))))\n",
    ),
    Task(
        "top-words",
        "Input is {text: string, k: nonnegative integer}. Extract ASCII letter words, "
        "case-insensitively. Return up to k [word,count] pairs, ordered by descending "
        "frequency, breaking ties alphabetically. Ignore punctuation and digits.",
        (({"text": "E2B runs code. Code runs safely!", "k": 3},
          [["code", 2], ["runs", 2], ["b", 1]]),
         ({"text": "Banana apple banana APPLE cherry", "k": 2},
          [["apple", 2], ["banana", 2]]),
         ({"text": "123 ...", "k": 5}, []),
         ({"text": "hello", "k": 0}, [])),
        "import json, sys\nfrom collections import Counter\nx=json.load(sys.stdin)\n"
        "print(json.dumps(Counter(x['text'].split()).most_common(x['k'])))\n",
    ),
    Task(
        "shortest-path",
        "Input is {graph: adjacency list object, start: string, end: string}. "
        "Return the minimum number of edges from start to end in a directed, "
        "unweighted graph, or -1 if unreachable. Missing nodes have no outgoing edges. "
        "Start equal to end has distance zero. Graphs may contain cycles.",
        (({"graph": {"a": ["b", "c"], "b": ["d"], "c": ["d"]},
           "start": "a", "end": "d"}, 2),
         ({"graph": {"a": ["b"], "b": ["a"]}, "start": "a", "end": "z"}, -1),
         ({"graph": {}, "start": "x", "end": "x"}, 0),
         ({"graph": {"a": ["d", "b"], "b": ["c"], "c": ["d"]},
           "start": "a", "end": "d"}, 1)),
        "import json, sys\nx=json.load(sys.stdin)\n"
        "print(1 if x['end'] in x['graph'].get(x['start'], []) else -1)\n",
    ),
)
