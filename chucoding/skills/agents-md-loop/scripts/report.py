#!/usr/bin/env python3
"""AGENTS.md 보강 루프의 결과 요약 표.

`measurements.csv` 에서 이번 스프린트 행과 같은 측정 정의 버전의 직전 측정 행을 골라
규칙별 PR당 지적 수 추이와 승격 후보를 고정 형식 목록으로 낸다. 보강 티켓 설명의 「결과 요약」 절과
댓글에 이 출력을 그대로 쓴다. HDIT 티켓 본문은 표를 쓰지 않으므로(chucoding:jira 「표 대신 쓰는 형식」)
표가 아니라 목록이다. 절차는 chucoding 플러그인 `agents-md-loop` 스킬의 SKILL.md 를 본다.

  python3 ~/.claude/skills/chucoding/skills/agents-md-loop/scripts/report.py --csv W/measurements.preview.csv --sprint 26_4_#4
"""
import argparse
import csv
import sys

PROMOTE_MIN_PRS = 3
TAIL_IDS = ["NO_RULE_ID", "LENS_RULE", "LENS_BUG", "LENS_ADVERSARIAL"]


def load(path):
    """행 목록과 측정 묶음 순서((sprint, def_version, ticket) 첫 등장 순)"""
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    order = []
    for r in rows:
        key = (r["sprint"], r["def_version"], r["ticket"])
        if key not in order:
            order.append(key)
    return rows, order


def pick(order, sprint, ticket=""):
    """이번 묶음과 같은 정의 버전의 직전 묶음. 직전이 없으면 None"""
    cur = [k for k in order if k[0] == sprint and (not ticket or k[2] == ticket)]
    if len(cur) != 1:
        sys.exit(f"스프린트 {sprint} 의 측정 묶음이 {len(cur)}개다. --ticket 으로 하나를 고른다")
    cur = cur[0]
    before = [k for k in order[:order.index(cur)] if k[1] == cur[1]]
    return cur, (before[-1] if before else None)


def index(rows, key):
    """(metric, rule_id) → 행"""
    return {(r["metric"], r["rule_id"]): r for r in rows if (r["sprint"], r["def_version"], r["ticket"]) == key}


def fmt_delta(cur, prev):
    """rate 변화. 둘 중 하나가 없으면 -"""
    if cur == "" or prev == "":
        return "-"
    d = float(cur) - float(prev)
    return f"{d:+.2f}"


def report(rows, cur, prev, promote_min=PROMOTE_MIN_PRS):
    """마크다운 요약. 스프린트 사이에 나란히 읽도록 줄 형식을 고정한 목록(표 없음)"""
    c = index(rows, cur)
    p = index(rows, prev) if prev else {}
    get = lambda idx, m, r, k="rate": idx.get((m, r), {}).get(k, "")
    scope = get(c, "scope_prs", "", "value")
    lines = [
        f"측정 {cur[0]} ({cur[2]}, 정의 {cur[1]}), 직전 {prev[0] + ' (' + prev[2] + ')' if prev else '없음'}",
        f"범위 PR {scope}건, 자동 리뷰 지적 {get(c, 'auto_findings', 'ALL', 'value')}건"
        f" (PR당 {get(c, 'auto_findings', 'ALL')}, 직전 {get(p, 'auto_findings', 'ALL') or '-'})",
        "",
        "규칙별 PR당 지적 수 (직전 → 이번, 변화, 이번 지적 수, 지적이 나온 PR 수)",
    ]
    rule_ids = sorted({r for (m, r) in list(c) + list(p) if m == "auto_findings" and r not in ["ALL", *TAIL_IDS]})
    promote = []
    for rid in rule_ids + TAIL_IDS:
        cur_rate, prev_rate = get(c, "auto_findings", rid) or ("0.00" if rid not in TAIL_IDS else ""), get(p, "auto_findings", rid)
        prs = get(c, "auto_findings_prs", rid, "value")
        is_promote = rid not in TAIL_IDS and prs != "" and int(prs) >= promote_min
        if is_promote:
            promote.append(rid)
        lines.append(f"* `{rid}` {prev_rate or '-'} → {cur_rate or '-'} ({fmt_delta(cur_rate, prev_rate)}), "
                     f"지적 {get(c, 'auto_findings', rid, 'value') or 0}건, PR {prs or 0}개"
                     f"{', 승격 후보' if is_promote else ''}")
    code = sorted({m for (m, _) in list(c) + list(p) if m.startswith("code:")})
    if code:
        lines += ["", "코드 지표 (추가 1천 줄당 직전 → 이번, 이번 건수)"]
        for m in code:
            rid = next((r for (mm, r) in list(c) + list(p) if mm == m), "")
            lines.append(f"* `{m[5:]}`{(' (`' + rid + '`)') if rid else ''} {get(p, m, rid) or '-'} → {get(c, m, rid) or '-'}, "
                         f"{get(c, m, rid, 'value') or '-'}건")
    lines += ["", f"승격 후보(이번 측정에서 {promote_min}개 PR 이상 반복): " + (", ".join(f"`{r}`" for r in promote) or "없음")]
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", required=True)
    p.add_argument("--sprint", required=True)
    p.add_argument("--ticket", default="", help="같은 스프린트에 측정 묶음이 둘 이상일 때 고른다")
    p.add_argument("--promote-min", type=int, default=PROMOTE_MIN_PRS)
    a = p.parse_args(argv)
    rows, order = load(a.csv)
    cur, prev = pick(order, a.sprint, a.ticket)
    sys.stdout.write(report(rows, cur, prev, a.promote_min))


if __name__ == "__main__":
    main()
