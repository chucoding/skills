#!/usr/bin/env python3
"""AGENTS.md 보강 루프 측정의 집계 단계.

`collect.py` 가 채운 작업 폴더를 읽어 측정 기간의 지표를 `measurements.csv` 행 형식으로 낸다.
절차는 chucoding 플러그인 `agents-md-loop` 스킬의 SKILL.md, 측정 정의 버전과 칸의 뜻은
위키 `homedot-hub/knowledge/standards/effect/measurement.md` 를 본다.

  # 집계해 행 파일로 저장(위키를 건드리지 않음)
  python3 ~/.claude/skills/chucoding/skills/agents-md-loop/scripts/measure.py --work W \
      --start 2026-11-16T00:00:00+09:00 --end 2026-11-27T00:00:00+09:00 \
      --sprint 26_4_#4 --ticket HDIT-1234 > W/rows.csv
  # 위키 워크스페이스에서 행 파일을 그대로 덧붙임(키 중복이면 거절)
  python3 ~/.claude/skills/chucoding/skills/agents-md-loop/scripts/measure.py --rows W/rows.csv \
      --append homedot-hub/knowledge/standards/effect/measurements.csv

부산물
  W/items.jsonl      자동 리뷰 지적 한 건에 한 줄(규칙 ID, 렌즈, 제목). 군집 분류가 필요할 때 에이전트가 읽는다
  W/code_rows.json   PR별 코드 지표
"""
import argparse
import collections
import csv
import datetime as dt
import json
import os
import re
import sys

DEFAULT_REVIEWER = "hyeonseok-suh"
DEFAULT_DEF_VERSION = "v1"
# 측정 정의 v1 의 제외 PR. 승격과 통합 PR
DEFAULT_EXCLUDE = "2339,2348,2528,2539,2626,2666"
AUTO_MARK = "pr-auto-review"

CSV_FIELDS = ["sprint", "measured_at", "period_start", "period_end", "def_version", "ticket",
              "metric", "rule_id", "value", "denominator", "rate"]

# 허브 기준서 규칙 ID(standards/README.md 「규칙 ID 체계」)와, 기준서 밖 관행 지적에 자동 리뷰가 붙이는 CONV
RULE_ID = re.compile(r"\b(?:FSD|REUSE|RQ|STATE|FORM|GRID|UI|MOCK|TS|CODE)-\d{2}\b|\bCONV\b")
FINDING = re.compile(r"^### (P[1-4])\s*(.+?)\n(.*?)(?=^### |\Z)", re.M | re.S)
LENS = re.compile(r"\((버그|적대적|규칙)[^)]*리뷰\)")
LENS_IDS = {"버그": "LENS_BUG", "적대적": "LENS_ADVERSARIAL", "규칙": "LENS_RULE"}

# 코드 지표. (이름, 규칙 ID, 판정). 판정은 추가된 한 줄과 파일 정보를 받아 참이면 1건
CODE_LINE_METRICS = [
    ("rq-await-void-invalidate", "RQ-04", lambda l, f: re.search(r"\b(await|void)\s+[\w.?]*invalidateQueries", l)),
    ("rq-mutate-async", "RQ-06", lambda l, f: re.search(r"\bmutateAsync\b", l)),
    ("rq-set-query-data", "RQ-03", lambda l, f: re.search(r"\bsetQueryData\b", l)),
    ("rq-remove-queries", "RQ-03", lambda l, f: re.search(r"\bremoveQueries\b", l)),
    ("rq-reset-queries", "RQ-03", lambda l, f: re.search(r"\bresetQueries\b", l)),
    ("search-memory", "STATE-01", lambda l, f: "searchMemory" in l),
    ("dayjs-direct-import", "REUSE-02",
     lambda l, f: re.search(r"^\s*import\b.*from\s+['\"]dayjs['\"/]", l) and not f.startswith("src/shared/lib/date")),
    ("column-builder-decl", "FSD-05", lambda l, f: re.search(r"\b(build|create|make)\w*Columns?\b\s*[=(:]", l)),
    # 화면 코드(shared 밖)가 gridRef 의 api 를 직접 부르거나 읽는 줄. 공개 함수 인자로 넘기는 줄은 아래로 따로 센다
    ("grid-api-direct", "GRID-07",
     lambda l, f: not f.startswith("src/shared/") and re.search(r"[Gg]ridRef\.current\??\.api\??\.\w", l)),
    ("grid-api-public-fn-arg", "GRID-07",
     lambda l, f: not f.startswith("src/shared/") and re.search(r"[(,]\s*[\w.]*[Gg]ridRef\.current\??\.api\b\s*[,)]", l)),
    # HDIT-6655 에서 더한 지표
    ("page-use-editable-grid-rows", "GRID-02", lambda l, f: f.startswith("src/pages/") and "useEditableGridRows(" in l),
    ("as-unknown-as", "TS-01", lambda l, f: re.search(r"\bas unknown as\b", l)),
    ("number-converter-redefined", "REUSE-04",
     lambda l, f: not f.startswith("src/shared/")
     and re.search(r"\b(function|const|let)\s+(toNullableNumber|toOptionalNumber)\b", l)),
]
# 새 파일 단위 지표. (이름, 규칙 ID, 경로 판정)
CODE_FILE_METRICS = [
    ("new-column-file", "FSD-05",
     lambda p: counted(p) and re.search(r"(^|/)(\w+-)?columns?(-builder)?\.(ts|tsx)$|column-?builder", p)),
    ("new-model-test-file", "CODE-10", lambda p: p.startswith("src/") and re.search(r"/model/[^/]+\.test\.tsx?$", p)),
    ("new-scripts-file", "", lambda p: p.startswith("scripts/")),
]
CODE_METRIC_RULES = {n: r for n, r, _ in CODE_LINE_METRICS + CODE_FILE_METRICS}


def counted(path):
    """추가 줄 수와 줄 단위 지표를 세는 파일. src 아래 ts, tsx 중 생성 파일, 테스트, 스토리 제외"""
    return (path.startswith("src/") and re.search(r"\.(ts|tsx)$", path)
            and not re.search(r"types\.gen\.ts$|\.test\.|\.spec\.|\.stories\.", path))


def parse_time(s):
    """ISO 시각 문자열을 시간대가 있는 datetime 으로. 시간대가 없으면 UTC 로 본다"""
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def read_text(path, default=""):
    """파일 내용. 없으면 default"""
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def load_json(path, default=None):
    """JSON 파일. 없거나 비었으면 default(기본 빈 배열)"""
    text = read_text(path)
    return json.loads(text) if text.strip() else ([] if default is None else default)


def login(item):
    """리뷰와 코멘트 작성자 계정. 삭제된 계정은 user 가 null 이라 None"""
    return (item.get("user") or {}).get("login")


def rule_ids(title):
    """지적 제목에 붙은 규칙 ID 목록(중복 제거, 정렬)"""
    return sorted(set(RULE_ID.findall(title)))


def extract_findings(n, reviews, comments, reviewer):
    """한 PR 의 자동 리뷰 지적 추출. 라운드마다 다시 올라오는 같은 제목은 한 건으로 침"""
    items, seen = [], set()

    def add(source, level, title, rest, ref):
        key = re.sub(r"\W", "", title)[:60]
        if key in seen:
            return
        seen.add(key)
        lens = LENS.search(rest)
        items.append(dict(pr=n, source=source, level=level, lens=lens.group(1) if lens else None,
                          rule_ids=rule_ids(title), title=title, ref=ref))

    for r in sorted(reviews, key=lambda x: x.get("submitted_at") or ""):
        body = (r.get("body") or "").strip()
        if login(r) != reviewer or not r.get("submitted_at") or AUTO_MARK not in body:
            continue
        for m in FINDING.finditer(body):
            add("auto-body", m.group(1), m.group(2).strip(), m.group(3), f"review-{r['id']}")
    for c in comments:
        body = c.get("body") or ""
        if login(c) != reviewer or c.get("in_reply_to_id") or AUTO_MARK not in body:
            continue
        first = next((ln for ln in body.splitlines() if ln.strip() and not ln.startswith("<!--")), "")
        add("auto-inline", None, first.lstrip("#* ").strip(), body, f"comment-{c['id']}")
    return items


def parse_diff(text):
    """diff 를 파일별 {path, new, add[]} 로 쪼갬"""
    files, cur = [], None
    for line in text.splitlines():
        if line.startswith("diff --git"):
            cur = {"path": line.split(" b/")[-1].strip(), "new": False, "add": []}
            files.append(cur)
        elif cur is not None:
            if line.startswith("new file mode"):
                cur["new"] = True
            elif line.startswith("+") and not line.startswith("+++"):
                cur["add"].append(line[1:])
    return files


def code_metrics(diff_text):
    """한 PR 의 추가 줄 수와 코드 지표 건수"""
    hits, added = collections.Counter(), 0
    for f in parse_diff(diff_text):
        path = f["path"]
        if f["new"]:
            for name, _, test in CODE_FILE_METRICS:
                if test(path):
                    hits[name] += 1
        if not counted(path):
            continue
        added += len(f["add"])
        for line in f["add"]:
            for name, _, test in CODE_LINE_METRICS:
                if test(line, path):
                    hits[name] += 1
    return added, hits


def agent_coauthored(meta):
    """커밋에 Claude 공동 작성 표기가 있는 PR 인지"""
    commits = (meta or {}).get("commits") or []
    return any(re.search(r"Co-Authored-By: Claude", c.get("messageBody") or "", re.I) for c in commits)


CLAUDE_TRAILER = re.compile(r"^Co-Authored-By:\s*(Claude[^<\n]*?)\s*<", re.I | re.M)


def main_model(meta):
    """PR 커밋의 Claude 공동 작성 표기 중 가장 많이 나온 모델. 동률이면 가장 늦게 작성된 커밋의 모델, 없으면 NONE"""
    seen = []
    for c in (meta or {}).get("commits") or []:
        for m in CLAUDE_TRAILER.findall(c.get("messageBody") or ""):
            seen.append((c.get("authoredDate") or "", " ".join(m.split())))
    if not seen:
        return "NONE"
    count = collections.Counter(m for _, m in seen)
    top = max(count.values())
    return max((t, m) for t, m in seen if count[m] == top)[1]


def review_count(reviews, reviewer):
    """리뷰어가 제출한 리뷰 수(자동 리뷰 포함, 상태 무관)"""
    return sum(1 for r in reviews if login(r) == reviewer and r.get("submitted_at"))


def commits_after_first_review(reviews, meta, reviewer):
    """리뷰어의 첫 리뷰 뒤에 작성된 커밋 수. 리베이스는 커밋 시각만 바꾸므로 작성 시각(authoredDate)으로 본다"""
    times = sorted(r["submitted_at"] for r in reviews if login(r) == reviewer and r.get("submitted_at"))
    if not times:
        return 0
    first = parse_time(times[0])
    return sum(1 for c in (meta or {}).get("commits") or []
               if c.get("authoredDate") and parse_time(c["authoredDate"]) > first)


def median(values):
    """중앙값. 빈 목록이면 None"""
    v = sorted(values)
    if not v:
        return None
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def first_review(reviews, reviewer):
    """리뷰어의 첫 리뷰. (자동 여부, 승인 여부), 없으면 None"""
    rv = sorted((r for r in reviews if login(r) == reviewer and r.get("submitted_at")),
                key=lambda r: r["submitted_at"])
    if not rv:
        return None
    return AUTO_MARK in (rv[0].get("body") or ""), rv[0]["state"] == "APPROVED"


def rate(value, denominator, per=1):
    """비율 문자열. 분모가 0 이면 빈 칸"""
    return f"{value / denominator * per:.2f}" if denominator else ""


def build_rows(meta, scope_prs, findings, code=None, extra=None, code_names=None):
    """지표를 measurements.csv 행으로 변환

    meta: sprint, measured_at, period_start, period_end, def_version, ticket
    findings: 자동 리뷰 지적 목록(rule_ids, lens 칸 필요)
    code: (src 추가 줄 수, 지표 Counter) 또는 None(코드 지표 행을 내지 않음)
    extra: [(metric, rule_id, value, denominator)] 또는 rate 를 직접 정한 (metric, rule_id, value, denominator, rate)
    code_names: 행으로 낼 코드 지표 이름. 비우면 정의된 지표 전부(0건도 행을 낸다)
    """
    rows = []

    def row(metric, rule_id, value, denominator="", r=""):
        rows.append({**meta, "metric": metric, "rule_id": rule_id, "value": value,
                     "denominator": denominator, "rate": r})

    row("scope_prs", "", scope_prs)
    row("auto_reviewed_prs", "", len({f["pr"] for f in findings}))
    row("auto_findings", "ALL", len(findings), scope_prs, rate(len(findings), scope_prs))
    by_rule = collections.Counter(i for f in findings for i in f["rule_ids"])
    for rid in sorted(by_rule):
        row("auto_findings", rid, by_rule[rid], scope_prs, rate(by_rule[rid], scope_prs))
    # 같은 규칙이 몇 개 PR 에서 나왔는지. 승격 후보(3개 PR 이상 반복) 판정에 쓴다
    prs_by_rule = collections.defaultdict(set)
    for f in findings:
        for i in f["rule_ids"]:
            prs_by_rule[i].add(f["pr"])
    for rid in sorted(prs_by_rule):
        row("auto_findings_prs", rid, len(prs_by_rule[rid]), scope_prs, rate(len(prs_by_rule[rid]), scope_prs))
    no_id = sum(1 for f in findings if not f["rule_ids"])
    row("auto_findings", "NO_RULE_ID", no_id, scope_prs, rate(no_id, scope_prs))
    by_lens = collections.Counter(f["lens"] for f in findings if f["lens"])
    for lens in ["규칙", "버그", "적대적"]:
        row("auto_findings", LENS_IDS[lens], by_lens[lens], scope_prs, rate(by_lens[lens], scope_prs))
    if code is not None:
        added, hits = code
        row("src_added_lines", "", added)
        for name in code_names or CODE_METRIC_RULES:
            row(f"code:{name}", CODE_METRIC_RULES[name], hits.get(name, 0), added, rate(hits.get(name, 0), added, 1000))
    for item in extra or []:
        metric, rid, value, denominator = item[:4]
        r = item[4] if len(item) > 4 else (rate(value, denominator) if denominator != "" else "")
        row(metric, rid, value, denominator, r)
    return rows


def measure(work, start, end, exclude, reviewer):
    """작업 폴더에서 기간 안 범위 PR 의 지적, 코드 지표, 첫 리뷰를 모음"""
    prs = {p["number"]: p for p in load_json(os.path.join(work, "prs.json"))}
    nums = [int(x) for x in read_text(os.path.join(work, "nums.txt")).split()]
    lo, hi = parse_time(start), parse_time(end) if end else None
    scope = [n for n in nums if n not in exclude and n in prs
             and lo <= parse_time(prs[n]["createdAt"]) and (hi is None or parse_time(prs[n]["createdAt"]) < hi)]
    findings, code_rows = [], []
    added, hits = 0, collections.Counter()
    first = collections.Counter()
    agent = 0
    models, rounds, fixes, lead = collections.Counter(), 0, 0, []
    for n in scope:
        raw = os.path.join(work, "raw", str(n))
        missing = [k for k in ("reviews.json", "comments.json", "meta.json")
                   if not os.path.exists(f"{raw}.{k}") or os.path.exists(f"{raw}.{k}.error")]
        if missing:
            # 받지 못한 파일은 빈 목록으로 읽혀 지적 0건으로 들어간다. collect.py --refresh 로 다시 받고 해석에 적는다
            print(f"경고: #{n} {', '.join(missing)} 수집 실패, 지적이 0건으로 들어감", file=sys.stderr)
        reviews = load_json(f"{raw}.reviews.json")
        findings += extract_findings(n, reviews, load_json(f"{raw}.comments.json"), reviewer)
        if not os.path.exists(f"{raw}.diff"):
            # diff 를 받지 못한 PR 은 코드 지표가 0 으로 들어간다. 측정 해석에 적는다
            print(f"경고: #{n} diff 없음, 코드 지표에서 빠짐", file=sys.stderr)
        a, h = code_metrics(read_text(f"{raw}.diff"))
        added += a
        hits.update(h)
        pr_meta = load_json(f"{raw}.meta.json", {})
        ag = agent_coauthored(pr_meta)
        agent += ag
        models[main_model(pr_meta)] += 1
        rounds += review_count(reviews, reviewer)
        fixes += commits_after_first_review(reviews, pr_meta, reviewer)
        if prs[n].get("mergedAt"):
            lead.append((parse_time(prs[n]["mergedAt"]) - parse_time(prs[n]["createdAt"])).total_seconds() / 3600)
        fr = first_review(reviews, reviewer)
        if fr:
            kind = "AUTO" if fr[0] else "HUMAN"
            first[(kind, "all")] += 1
            first[(kind, "approved")] += fr[1]
        code_rows.append(dict(pr=n, added=a, hits=dict(h), agent_coauthored=ag))
    extra = [("agent_coauthored_prs", "", agent, len(scope))]
    for kind in ["AUTO", "HUMAN"]:
        extra.append(("first_review_approved", kind, first[(kind, "approved")], first[(kind, "all")]))
    # 시간 절약 지표(보정 2). 측정 정의 버전은 그대로 두고 지표만 더한다
    for model in sorted(models):
        extra.append(("main_model_share", model, models[model], len(scope)))
    extra.append(("review_rounds", "", rounds, len(scope)))
    extra.append(("fix_commits_after_first_review", "", fixes, len(scope)))
    m = median(lead)
    extra.append(("merge_lead_time_hours", "", "" if m is None else f"{m:.1f}", len(lead), ""))
    return scope, findings, (added, hits), code_rows, extra


def existing_keys(path):
    """이미 쌓인 행의 (sprint, def_version, ticket, metric, rule_id) 집합"""
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8", newline="") as f:
        return {(r["sprint"], r["def_version"], r["ticket"], r["metric"], r["rule_id"]) for r in csv.DictReader(f)}


def write_rows(rows, out, append_path=None):
    """행을 표준 출력 또는 measurements.csv 끝에 씀. 같은 키가 이미 있으면 추가하지 않음"""
    if append_path:
        keys = existing_keys(append_path)
        dup = [r for r in rows if (r["sprint"], r["def_version"], r["ticket"], r["metric"], r["rule_id"]) in keys]
        if dup:
            sys.exit(f"이미 같은 스프린트, 정의 버전, 티켓의 행이 {len(dup)}개 있다. 고치지 말고 sprint 나 ticket 을 바꿔 새로 쌓는다")
        new_file = not os.path.exists(append_path) or os.path.getsize(append_path) == 0
        with open(append_path, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, CSV_FIELDS, lineterminator="\n")
            if new_file:
                w.writeheader()
            w.writerows(rows)
        return
    w = csv.DictWriter(out, CSV_FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)


def read_rows(path):
    """이전에 표준 출력으로 저장한 행 파일. 헤더가 CSV_FIELDS 와 다르면 거절"""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != CSV_FIELDS:
            sys.exit(f"{path} 의 헤더가 measurements.csv 칸과 다르다: {reader.fieldnames}")
        rows = list(reader)
    if not rows:
        sys.exit(f"{path} 에 행이 없다")
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--work", default="", help="collect.py 작업 폴더")
    p.add_argument("--start", default="", help="PR 생성 시각 하한(포함). 시간대를 붙인 ISO 시각")
    p.add_argument("--end", default=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                   help="PR 생성 시각 상한(제외). 기본값은 실행 시각이고 그 값이 period_end 칸에 남아 다음 측정의 시작이 된다")
    p.add_argument("--exclude", default=DEFAULT_EXCLUDE, help="제외 PR 번호, 쉼표 구분")
    p.add_argument("--reviewer", default=DEFAULT_REVIEWER)
    p.add_argument("--sprint", default="", help="측정한 스프린트 이름(예: 26_4_#4)")
    p.add_argument("--ticket", default="", help="측정 티켓 키")
    p.add_argument("--def-version", default=DEFAULT_DEF_VERSION)
    p.add_argument("--measured-at", default=dt.date.today().isoformat())
    p.add_argument("--append", default="", help="행을 덧붙일 measurements.csv 경로. 비우면 표준 출력")
    p.add_argument("--rows", default="",
                   help="집계하지 않고 이 행 파일(이전 표준 출력)을 --append 에 그대로 덧붙인다. 위키 워크스페이스에서 쓴다")
    a = p.parse_args(argv)

    if a.rows:
        if not a.append:
            p.error("--rows 는 --append 와 함께 쓴다")
        rows = read_rows(a.rows)
        write_rows(rows, sys.stdout, a.append)
        print(f"{a.append} 에 {len(rows)}행 덧붙임", file=sys.stderr)
        return
    missing = [n for n in ("work", "start", "sprint", "ticket") if not getattr(a, n)]
    if missing:
        p.error("집계에는 " + ", ".join(f"--{n}" for n in missing) + " 가 필요하다")

    exclude = {int(x) for x in a.exclude.split(",") if x.strip()}
    scope, findings, code, code_rows, extra = measure(a.work, a.start, a.end, exclude, a.reviewer)
    with open(os.path.join(a.work, "items.jsonl"), "w", encoding="utf-8") as f:
        for it in findings:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    with open(os.path.join(a.work, "code_rows.json"), "w", encoding="utf-8") as f:
        json.dump(code_rows, f, ensure_ascii=False, indent=1)
    meta = dict(sprint=a.sprint, measured_at=a.measured_at, period_start=a.start, period_end=a.end,
                def_version=a.def_version, ticket=a.ticket)
    write_rows(build_rows(meta, len(scope), findings, code, extra), sys.stdout, a.append or None)
    print(f"범위 PR {len(scope)}건, 자동 리뷰 지적 {len(findings)}건", file=sys.stderr)


if __name__ == "__main__":
    main()
