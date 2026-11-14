#!/usr/bin/env python3
"""measure.py 의 측정 정의 v1 을 합성 작업 폴더로 고정하는 테스트. 네트워크를 쓰지 않는다

  python3 ~/.claude/skills/chucoding/skills/agents-md-loop/scripts/measure.test.py -q

환경변수 MEASUREMENTS_CSV 에 위키 measurements.csv 경로를 주면 그 파일의 형식과 키 중복도 본다
"""
import contextlib
import csv
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("measure", os.path.join(HERE, "measure.py"))
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)
spec = importlib.util.spec_from_file_location("report", os.path.join(HERE, "report.py"))
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)
spec = importlib.util.spec_from_file_location("period", os.path.join(HERE, "period.py"))
period = importlib.util.module_from_spec(spec)
spec.loader.exec_module(period)

R = "hyeonseok-suh"
AUTO_BODY = """<!-- pr-auto-review sha=abc -->
요약

### P2 `GRID-02` `STATE-02` 행 사본을 둔다
- 위치: `src/pages/erp/a/ui/AGrid.tsx:10` (규칙 리뷰)
- 내용: 사본

### P4 저장 직후 옛 값이 보인다
- 위치: `src/pages/erp/a/APage.tsx:20` (버그 리뷰)
- 내용: 본문에 FSD-04 가 나와도 제목이 아니라 세지 않는다

### P3 `CONV` 이름이 관행과 다르다
- 위치: `src/pages/erp/a/api.ts:3` (적대적, 규칙 리뷰)
"""
# 다음 라운드. 같은 제목은 한 건으로 치고 새 제목만 더한다
AUTO_BODY_2 = """<!-- pr-auto-review sha=def -->
### P2 `GRID-02` `STATE-02` 행 사본을 둔다
- 위치: `src/pages/erp/a/ui/AGrid.tsx:10` (규칙 리뷰)

### P2 `FSD-04` 한 줄 함수를 export 한다
- 위치: `src/pages/erp/a/model/x.ts:1` (규칙 리뷰)
"""
DIFF = """diff --git a/src/pages/erp/a/ui/columns.ts b/src/pages/erp/a/ui/columns.ts
new file mode 100644
+export const buildAColumns = () => []
diff --git a/src/pages/erp/a/APage.tsx b/src/pages/erp/a/APage.tsx
+import dayjs from 'dayjs'
+gridRef.current?.api.forEachNode(() => {})
+addGridRows(gridRef.current?.api, rows)
+const v = x as unknown as Row
+const rows = useEditableGridRows(data)
+function toNullableNumber(v) { return v }
diff --git a/src/shared/lib/date.ts b/src/shared/lib/date.ts
+import dayjs from 'dayjs'
diff --git a/src/pages/erp/a/model/x.test.ts b/src/pages/erp/a/model/x.test.ts
new file mode 100644
+await queryClient.invalidateQueries()
"""


def review(i, at, body, state="COMMENTED", user=R):
    return {"id": i, "user": {"login": user}, "submitted_at": at, "state": state, "body": body}


class MeasureV1(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        w = self.work = self.tmp.name
        os.makedirs(os.path.join(w, "raw"))
        prs = [
            {"number": 1, "createdAt": "2026-11-16T01:00:00Z", "additions": 1, "deletions": 0},
            {"number": 2, "createdAt": "2026-11-17T01:00:00Z", "additions": 1, "deletions": 0},
            {"number": 3, "createdAt": "2026-11-18T01:00:00Z", "additions": 1, "deletions": 0},  # 제외 PR
            {"number": 4, "createdAt": "2026-11-15T14:59:59Z", "additions": 1, "deletions": 0},  # 기간 전(KST 11-15 23:59)
            {"number": 5, "createdAt": "2026-11-26T15:00:00Z", "additions": 1, "deletions": 0},  # 상한과 같음, 제외
        ]
        self.dump("prs.json", json.dumps(prs))
        self.dump("nums.txt", "1\n2\n3\n4\n5\n")
        self.write(1, "reviews", [review(10, "2026-11-16T02:00:00Z", AUTO_BODY, "CHANGES_REQUESTED"),
                                  review(11, "2026-11-16T03:00:00Z", AUTO_BODY_2, "APPROVED"),
                                  review(12, "2026-11-16T01:30:00Z", AUTO_BODY, user="someone")])
        self.write(1, "comments", [])
        self.dump("raw/1.diff", DIFF)
        self.write(1, "meta", {"commits": [{"messageBody": "x\n\nCo-Authored-By: Claude Opus <noreply@anthropic.com>"}]})
        self.write(2, "reviews", [review(20, "2026-11-17T02:00:00Z", "좋습니다", "APPROVED")])
        for n in (3, 4, 5):
            self.write(n, "reviews", [review(30 + n, "2026-11-18T02:00:00Z", AUTO_BODY)])

    def tearDown(self):
        self.tmp.cleanup()

    def dump(self, rel, text):
        with open(os.path.join(self.work, rel), "w", encoding="utf-8") as f:
            f.write(text)

    def write(self, n, kind, data):
        name = {"reviews": "reviews.json", "comments": "comments.json", "meta": "meta.json"}[kind]
        self.dump(f"raw/{n}.{name}", json.dumps(data, ensure_ascii=False))

    def run_measure(self):
        return measure.measure(self.work, "2026-11-16T00:00:00+09:00", "2026-11-27T00:00:00+09:00",
                               {3}, R)

    def test_period_and_exclude(self):
        scope, *_ = self.run_measure()
        self.assertEqual(scope, [1, 2])

    def test_findings_dedupe_and_rule_ids_from_title_only(self):
        _, findings, *_ = self.run_measure()
        self.assertEqual(len(findings), 4)
        ids = [f["rule_ids"] for f in findings]
        self.assertEqual(ids, [["GRID-02", "STATE-02"], [], ["CONV"], ["FSD-04"]])
        self.assertEqual([f["lens"] for f in findings], ["규칙", "버그", "적대적", "규칙"])

    def test_code_metrics(self):
        _, _, (added, hits), code_rows, _ = self.run_measure()
        self.assertEqual(added, 8)  # 테스트 파일 줄은 세지 않는다
        self.assertEqual(hits["new-column-file"], 1)
        self.assertEqual(hits["column-builder-decl"], 1)
        self.assertEqual(hits["dayjs-direct-import"], 1)  # shared/lib/date 는 제외
        self.assertEqual(hits["grid-api-direct"], 1)
        self.assertEqual(hits["grid-api-public-fn-arg"], 1)
        self.assertEqual(hits["as-unknown-as"], 1)
        self.assertEqual(hits["page-use-editable-grid-rows"], 1)
        self.assertEqual(hits["number-converter-redefined"], 1)
        self.assertEqual(hits["new-model-test-file"], 1)
        self.assertEqual(hits["rq-await-void-invalidate"], 0)  # 테스트 파일 안이라 세지 않는다
        self.assertTrue(code_rows[0]["agent_coauthored"])

    def test_deleted_user_does_not_crash(self):
        reviews = json.load(open(os.path.join(self.work, "raw", "1.reviews.json"), encoding="utf-8"))
        reviews.append({"id": 99, "user": None, "submitted_at": "2026-11-16T04:00:00Z", "state": "COMMENTED", "body": AUTO_BODY})
        self.write(1, "reviews", reviews)
        self.write(1, "comments", [{"id": 5, "user": None, "body": AUTO_BODY}])
        _, findings, *_ = self.run_measure()
        self.assertEqual(len(findings), 4)

    def test_collect_failure_warning(self):
        os.remove(os.path.join(self.work, "raw", "1.comments.json"))
        self.dump("raw/2.meta.json.error", "gh 실패")
        self.write(2, "comments", [])
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.run_measure()
        self.assertIn("#1 comments.json 수집 실패", err.getvalue())
        self.assertIn("#2 meta.json 수집 실패", err.getvalue())

    def test_no_failure_warning_when_complete(self):
        self.write(1, "comments", [])
        self.write(2, "comments", [])
        self.write(2, "meta", {"commits": []})
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.run_measure()
        self.assertNotIn("수집 실패", err.getvalue())

    def test_rows(self):
        scope, findings, code, _, extra = self.run_measure()
        meta = dict(sprint="S", measured_at="2026-11-26", period_start="a", period_end="b", def_version="v1", ticket="T")
        rows = measure.build_rows(meta, len(scope), findings, code, extra)
        get = {(r["metric"], r["rule_id"]): r for r in rows}
        self.assertEqual(get[("scope_prs", "")]["value"], 2)
        self.assertEqual(get[("auto_reviewed_prs", "")]["value"], 1)
        self.assertEqual(get[("auto_findings", "ALL")]["rate"], "2.00")
        self.assertEqual(get[("auto_findings", "GRID-02")]["value"], 1)
        self.assertEqual(get[("auto_findings_prs", "GRID-02")]["value"], 1)
        self.assertEqual(get[("auto_findings", "NO_RULE_ID")]["value"], 1)
        self.assertEqual(get[("auto_findings", "LENS_RULE")]["value"], 2)
        self.assertEqual(get[("code:dayjs-direct-import", "REUSE-02")]["rate"], "125.00")
        self.assertEqual(get[("first_review_approved", "AUTO")]["value"], 0)
        self.assertEqual(get[("first_review_approved", "AUTO")]["denominator"], 1)
        self.assertEqual(get[("first_review_approved", "HUMAN")]["value"], 1)
        self.assertEqual(get[("agent_coauthored_prs", "")]["value"], 1)

    def test_append_refuses_duplicates(self):
        meta = dict(sprint="S", measured_at="d", period_start="a", period_end="b", def_version="v1", ticket="T")
        rows = measure.build_rows(meta, 0, [], None, None)
        path = os.path.join(self.work, "m.csv")
        measure.write_rows(rows, io.StringIO(), path)
        with self.assertRaises(SystemExit):
            measure.write_rows(rows, io.StringIO(), path)
        with open(path, newline="") as f:
            self.assertEqual(next(csv.reader(f)), measure.CSV_FIELDS)


class AppendRows(unittest.TestCase):
    """measure.py --rows 가 저장한 행 파일을 그대로 덧붙이고 중복은 거절하는지"""

    def test_rows_file_append(self):
        meta = dict(sprint="S", measured_at="d", period_start="a", period_end="b", def_version="v1", ticket="T")
        rows = measure.build_rows(meta, 2, [dict(pr=1, lens="규칙", rule_ids=["FSD-04"])], None, None)
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            measure.write_rows(rows, out)
            rows_path, csv_path = os.path.join(tmp, "rows.csv"), os.path.join(tmp, "m.csv")
            with open(rows_path, "w", encoding="utf-8") as f:
                f.write(out.getvalue())
            measure.main(["--rows", rows_path, "--append", csv_path])
            with open(csv_path, encoding="utf-8") as f:
                self.assertEqual(f.read(), out.getvalue())
            with self.assertRaises(SystemExit):
                measure.main(["--rows", rows_path, "--append", csv_path])
            with self.assertRaises(SystemExit):
                measure.main(["--rows", rows_path])  # --append 없이는 거절


class CollectSince(unittest.TestCase):
    """collect.py 가 GitHub 검색 날짜를 UTC 기준 하루 앞당겨 기간 초반 PR 을 놓치지 않는지"""

    def test_search_date(self):
        spec = importlib.util.spec_from_file_location("collect", os.path.join(HERE, "collect.py"))
        collect = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(collect)
        self.assertEqual(collect.search_date("2026-11-16T00:00:00+09:00"), "2026-11-14")  # UTC 11-15 15:00
        self.assertEqual(collect.search_date("2026-11-20T01:00:00Z"), "2026-11-19")
        self.assertEqual(collect.search_date("2026-11-16"), "2026-11-15")  # 시간대 없는 날짜는 UTC 로 본다
        with self.assertRaises(ValueError):
            collect.search_date("11/16")


class Period(unittest.TestCase):
    """period.py 가 직전 보강 PR 머지 시각, 없으면 CSV 마지막 행 종료를 기간 시작으로 고르는지"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = os.path.join(self.tmp.name, "m.csv")
        meta = dict(sprint="26_4_#3", measured_at="d", period_start="a", period_end="2026-11-13T18:00:00+09:00",
                    def_version="v1", ticket="HDIT-4867")
        measure.write_rows(measure.build_rows(meta, 0, [], None, None), io.StringIO(), self.csv)

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def pr(n, merged_at, *paths):
        return {"number": n, "title": f"t{n}", "mergedAt": merged_at, "files": [{"path": x} for x in paths]}

    def test_latest_merged_agents_md_pr(self):
        merged = [self.pr(10, "2026-11-18T01:00:00Z", "AGENTS.md"),
                  self.pr(11, "2026-11-19T01:00:00Z", "src/a.ts"),  # AGENTS.md 를 안 바꾼 PR 은 무시
                  self.pr(12, "2026-11-20T01:00:00Z", "src/pages/AGENTS.md")]
        out = period.decide("HDIT-1", merged, [], self.csv)
        self.assertEqual(out["start"], "2026-11-20T01:00:00Z")
        self.assertIn("#12", out["basis"])
        self.assertEqual([p["number"] for p in out["merged"]], [10, 12])

    def test_fallback_to_csv_when_not_merged(self):
        out = period.decide("HDIT-1", [], [self.pr(20, None, "AGENTS.md")], self.csv)
        self.assertEqual(out["start"], "2026-11-13T18:00:00+09:00")
        self.assertIn("아직 머지 전", out["basis"])
        self.assertEqual(out["open"], [20])

    def test_fallback_without_pr(self):
        out = period.decide("HDIT-1", [], [], self.csv)
        self.assertTrue(out["basis"].startswith("HDIT-1 보강 PR 없음."))


class Report(unittest.TestCase):
    """report.py 가 같은 정의 버전의 직전 측정과 비교하고 승격 후보를 고르는지"""

    def test_trend_and_promote(self):
        def rows(sprint, ver, ticket, findings, prs):
            meta = dict(sprint=sprint, measured_at="d", period_start="a", period_end="b", def_version=ver, ticket=ticket)
            fs = [dict(pr=p, lens="규칙", rule_ids=[rid]) for rid, n in findings.items() for p in range(n)]
            return measure.build_rows(meta, prs, fs, None, None)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.csv")
            measure.write_rows(rows("S1", "v1", "T1", {"FSD-04": 4}, 10), io.StringIO(), path)
            measure.write_rows(rows("S2", "v2", "T2", {"FSD-04": 1}, 10), io.StringIO(), path)  # 정의가 다르면 건너뛴다
            measure.write_rows(rows("S3", "v1", "T3", {"FSD-04": 3, "GRID-02": 1}, 10), io.StringIO(), path)
            data, order = report.load(path)
            cur, prev = report.pick(order, "S3")
            self.assertEqual(prev, ("S1", "v1", "T1"))
            out = report.report(data, cur, prev)
            self.assertIn("* `FSD-04` 0.40 → 0.30 (-0.10), 지적 3건, PR 3개, 승격 후보\n", out)
            self.assertIn("* `GRID-02` - → 0.10 (-), 지적 1건, PR 1개\n", out)
            self.assertNotIn("|", out)  # 티켓 본문에 표를 쓰지 않는다
            self.assertIn("승격 후보(이번 측정에서 3개 PR 이상 반복): `FSD-04`", out)
            _, first_prev = report.pick(order, "S1")
            self.assertIsNone(first_prev)


class RepoCsv(unittest.TestCase):
    """저장소의 measurements.csv 가 형식을 지키는지"""

    def test_header_and_unique_keys(self):
        path = os.environ.get("MEASUREMENTS_CSV")
        if not path:
            self.skipTest("MEASUREMENTS_CSV 미지정")
        with open(path, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(list(rows[0].keys()), measure.CSV_FIELDS)
        keys = [(r["sprint"], r["def_version"], r["ticket"], r["metric"], r["rule_id"]) for r in rows]
        self.assertEqual(len(keys), len(set(keys)))


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], *sys.argv[1:]])
