#!/usr/bin/env python3
"""agents-md-regress 의 네트워크 없이 확인할 수 있는 부분(과제 형식, 비교군 만들기, 정규식 채점, 요약)을 고정하는 테스트

  python3 ~/.claude/skills/chucoding/skills/agents-md-regress/scripts/regress.test.py -q
"""
import csv
import glob
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import grade  # noqa: E402
import run  # noqa: E402
import summary  # noqa: E402

DIFF = """diff --git a/src/pages/erp/a/APage.tsx b/src/pages/erp/a/APage.tsx
+const v = x as unknown as Row
+gridRef.current?.api.forEachNode(() => {})
diff --git a/src/pages/erp/a/ui/columns.ts b/src/pages/erp/a/ui/columns.ts
new file mode 100644
+export const buildAColumns = () => []
"""
HINT_WORDS = ["as unknown", "export 하지", "gridRef", "규칙", "AGENTS.md", "FSD-", "TS-0", "GRID-", "REUSE-"]


class Tasks(unittest.TestCase):
    """tasks/*.json 이 실행기와 채점기가 읽는 형식을 지키는지"""

    def test_task_files(self):
        files = sorted(glob.glob(os.path.join(HERE, "..", "tasks", "*.json")))
        self.assertGreaterEqual(len(files), 5)
        for path in files:
            t = json.load(open(path, encoding="utf-8"))
            with self.subTest(task=t.get("id")):
                self.assertEqual(os.path.basename(path), f"{t['id']}.json")
                self.assertRegex(t["base_commit"], r"^[0-9a-f]{40}$")
                self.assertTrue(t["rules"])
                g = t["grading"]
                self.assertTrue(g.get("regex") or g.get("judge"))
                for name in g.get("regex") or []:
                    self.assertIn(name, grade.measure.CODE_METRIC_RULES)
                for w in HINT_WORDS:   # 프롬프트에 규칙 힌트를 넣지 않는다
                    self.assertNotIn(w, t["prompt"])
                self.assertIsInstance(t.get("agents_md_strip", []), list)


class Strip(unittest.TestCase):
    def test_strip_rules(self):
        text, removed = run.strip_rules("a\n- 한 곳에서만 쓰는 한 줄 함수\nb\n", ["한 줄 함수"])
        self.assertEqual((text, removed), ("a\nb\n", 1))


class Grade(unittest.TestCase):
    def test_regex_grading_uses_measure_metrics(self):
        task = {"id": "t", "grading": {"regex": ["as-unknown-as", "grid-api-direct", "new-column-file",
                                                 "column-builder-decl"], "judge": []}}
        got = {s["rule_id"]: s["violations"] for s in grade.grade(task, DIFF)}
        self.assertEqual(got, {"TS-01": 1, "GRID-07": 1, "FSD-05": 2})

    def test_judge_skipped_on_empty_diff(self):
        task = {"id": "t", "grading": {"regex": [], "judge": ["FSD-04"]}}
        self.assertEqual(grade.grade(task, "")[0]["violations"], 0)


class Summary(unittest.TestCase):
    def test_retire_and_recommend(self):
        def row(run_id, effort, variant, v, err="False"):
            return {f: "" for f in run.RUN_FIELDS} | dict(run_id=run_id, model="M", effort=effort, variant=variant,
                                                          rule_id="TS-01", violations=v, is_error=err,
                                                          input_tokens="100", output_tokens="10", cost_usd="0.1")
        rows = [row("a", "low", "full", "0"), row("b", "low", "full", "1"),
                row("c", "medium", "full", "0"), row("d", "medium", "full", "1"),
                row("e", "low", "stripped", "1"), row("f", "low", "stripped", "0"),
                row("g", "high", "full", "", "True")]
        out = summary.report(rows)
        self.assertIn("| M | low | full | 2 | 0 | 1/2 (50%)", out)
        self.assertIn("은퇴 후보(규칙 문장을 지워도 위반이 늘지 않음): `TS-01` (M, low", out)
        self.assertIn("M: `low`", out)
        self.assertIn("| M | high | full | 1 | 1 | -", out)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], *sys.argv[1:]])
