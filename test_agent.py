"""Credential-free orchestration checks; no generated Python runs on the host."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from e2b import CommandExitException

from agent import Execution, Executor, Writer, judge, solve
from tasks import TASKS


class AgentTests(unittest.TestCase):
    @patch("agent.Anthropic")
    def test_writer_extracts_source_and_rejects_truncated_program(self, client):
        response = Mock(stop_reason="end_turn", content=[
            Mock(type="thinking"), Mock(type="text", text="```python\nprint(1)\n```"),
        ])
        client.return_value.messages.create.return_value = response
        writer = Writer()
        self.assertEqual(writer.write([{"role": "user", "content": "task"}]), "print(1)")
        response.stop_reason = "max_tokens"
        with self.assertRaises(RuntimeError):
            writer.write([])

    def test_exit_and_json_are_both_required(self):
        for execution in (Execution(1, "2", "traceback"), Execution(0, "true", ""),
                          Execution(0, "not json", ""), Execution(0, "2\n2", "")):
            self.assertFalse(judge(1, {}, 2, execution)["passed"])
        self.assertTrue(judge(1, {}, 2, Execution(0, "2\n", ""))["passed"])

    def test_repair_receives_real_feedback_and_saves_artifacts(self):
        task = TASKS[0]
        failure = judge(1, task.cases[0][0], task.cases[0][1], Execution(0, "[]", ""))
        success = [judge(i, value, expected, Execution(0, json.dumps(expected), ""))
                   for i, (value, expected) in enumerate(task.cases, 1)]
        writer, executor = Mock(), Mock()
        writer.write.return_value = "repaired source"
        executor.evaluate.side_effect = [("first", [failure]), ("second", success)]
        with tempfile.TemporaryDirectory() as temp:
            self.assertTrue(solve(task, writer, executor, Path(temp), exercise_repair=True))
            self.assertEqual(executor.evaluate.call_args_list[0].args[0], task.buggy)
            messages = writer.write.call_args.args[0]
            self.assertIn(json.dumps([failure]), messages[2]["content"])
            record = json.loads((Path(temp) / "attempt-2.json").read_text())
            self.assertTrue(record["passed"])
            self.assertEqual(record["sandbox_id"], "second")

    def test_attempt_budget_stops_a_failing_agent(self):
        writer, executor = Mock(), Mock()
        writer.write.return_value = "bad source"
        executor.evaluate.return_value = ("sandbox", [{"passed": False}])
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(solve(TASKS[0], writer, executor, Path(temp), max_attempts=2))
        self.assertEqual(writer.write.call_count, 2)

    @patch.dict(os.environ, {"E2B_API_KEY": "unit-test-key"})
    @patch("agent.Sandbox")
    def test_success_is_computed_from_remote_stdout(self, factory):
        sandbox = factory.create.return_value
        task = TASKS[0]
        responses = []
        for _, expected in task.cases:
            responses.extend([Mock(exit_code=0), Mock(stdout=json.dumps(expected)), Mock(stdout="")])
        sandbox.commands.run.side_effect = responses
        _, reports = Executor().evaluate("source stored, never run locally", task)
        self.assertEqual(len(reports), 4)
        self.assertTrue(all(report["passed"] for report in reports))
        sandbox.files.write.assert_any_call("/home/user/solution.py", "source stored, never run locally")
        sandbox.kill.assert_called_once()

    @patch.dict(os.environ, {"E2B_API_KEY": "unit-test-key"})
    @patch("agent.Sandbox")
    def test_nonzero_exit_is_feedback_and_sandbox_is_killed(self, factory):
        sandbox = factory.create.return_value
        sandbox.sandbox_id = "test-sandbox"
        sandbox.commands.run.side_effect = [
            CommandExitException("", "", 124, None),
            Mock(stdout=""), Mock(stdout="timed out"),
        ]
        sandbox_id, reports = Executor().evaluate("while True: pass", TASKS[0])
        self.assertEqual(sandbox_id, "test-sandbox")
        self.assertEqual(reports[0]["exit_code"], 124)
        self.assertFalse(reports[0]["passed"])
        factory.create.assert_called_once_with(
            api_key="unit-test-key", timeout=90, allow_internet_access=False,
            secure=True, metadata={"demo": "sandbox-loop", "task": "merge-intervals"},
        )
        sandbox.kill.assert_called_once()

    @patch.dict(os.environ, {"E2B_API_KEY": "unit-test-key"})
    @patch("agent.Sandbox")
    def test_infrastructure_failure_still_cleans_up(self, factory):
        sandbox = factory.create.return_value
        sandbox.files.write.side_effect = ConnectionError("broken transport")
        with self.assertRaises(ConnectionError):
            Executor().evaluate("source", TASKS[0])
        sandbox.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
