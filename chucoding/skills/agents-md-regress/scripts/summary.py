#!/usr/bin/env python3
"""AGENTS.md 회귀 프롬프트 결과 요약.

run.py 의 runs.csv(또는 위키 regression-runs.csv)를 읽어 모델 × 추론 강도 × 변형별 규칙 위반률과 실행당 평균 토큰을
마크다운 표로 내고, 은퇴 후보와 권장 추론 강도를 고른다.

  python3 summary.py --csv W/runs.csv

- 위반률 = 위반이 1건 이상 나온 실행 수 / 채점된 실행 수. 오류 실행(is_error), 변경 없는 실행(no_change), 채점 실패
  (violations 빈칸)는 빼고 오류, 무변경, 채점 실패 칸에 따로 센다. 채점 실패는 실행이 아니라 규칙 ID 행 단위로 센다. 변경이 없는 실행을 위반 0건으로 세면 비교군 위반률이 낮아져 가짜 은퇴 후보가 생긴다.
- 은퇴 후보: 같은 모델 · 강도에서 규칙 문장을 지운 변형(stripped)의 위반률이 지우지 않은 변형(full)보다 높지 않은 규칙.
  규칙 문장 없이도 지킨다는 뜻이라 AGENTS.md 에서 뺄 후보다. 빼는 결정은 사람이 한다.
- 권장 추론 강도: 모델마다 full 변형의 전체 위반률이 가장 낮은 값과 같은 강도 중 가장 낮은 강도.
"""
import argparse
import collections
import csv
import sys

EFFORT_ORDER = ["low", "medium", "high", "xhigh", "max"]


def num(v):
    """빈칸이면 None"""
    return None if v in ("", None) else float(v)


def load(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def effort_key(e):
    return EFFORT_ORDER.index(e) if e in EFFORT_ORDER else len(EFFORT_ORDER)


def summarize(rows):
    """집계 dict: rates[(model, effort, variant, rule)] = (위반 실행, 채점 실행), runs[(model, effort, variant)] = 실행별 값"""
    rates = collections.defaultdict(lambda: [0, 0])
    errors = collections.Counter()
    no_change = collections.Counter()
    judge_failed = collections.Counter()
    runs = collections.defaultdict(dict)
    for r in rows:
        key = (r["model"], r["effort"], r["variant"])
        first_row = r["run_id"] not in runs[key]
        if r["is_error"] in ("True", "true", "1"):
            errors[key] += first_row
        elif r.get("no_change") in ("True", "true", "1"):
            no_change[key] += first_row
        runs[key][r["run_id"]] = r
        v = num(r["violations"])
        if r["is_error"] in ("True", "true", "1") or r.get("no_change") in ("True", "true", "1"):
            continue
        if v is None:
            judge_failed[key] += 1
            continue
        cell = rates[key + (r["rule_id"],)]
        cell[0] += v > 0
        cell[1] += 1
    return rates, runs, errors, no_change, judge_failed


def avg(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def report(rows):
    rates, runs, errors, no_change, judge_failed = summarize(rows)
    rules = sorted({k[3] for k in rates})
    keys = sorted(runs, key=lambda k: (k[0], effort_key(k[1]), k[2]))
    out = ["| 모델 | 강도 | 변형 | 실행 | 오류 | 무변경 | 채점 실패 | " + " | ".join(f"`{r}` 위반률" for r in rules)
           + " | 평균 입력 토큰 | 평균 출력 토큰 | 평균 비용 |",
           "|" + "---|" * (10 + len(rules))]
    for k in keys:
        rs = runs[k].values()
        cells = []
        for rule in rules:
            bad, n = rates.get(k + (rule,), (0, 0))
            cells.append(f"{bad}/{n} ({bad / n:.0%})" if n else "-")
        fmt = lambda v, f: "-" if v is None else f.format(v)
        tok_in = fmt(avg(num(r["input_tokens"]) for r in rs), "{:,.0f}")
        tok_out = fmt(avg(num(r["output_tokens"]) for r in rs), "{:,.0f}")
        cost = fmt(avg(num(r["cost_usd"]) for r in rs), "${:.3f}")
        out.append(f"| {k[0]} | {k[1]} | {k[2]} | {len(rs)} | {errors[k]} | {no_change[k]} | {judge_failed[k]} | " + " | ".join(cells)
                   + f" | {tok_in} | {tok_out} | {cost} |")

    retire = []
    for (model, effort, variant, rule), (bad, n) in sorted(rates.items()):
        if variant != "stripped" or not n:
            continue
        full = rates.get((model, effort, "full", rule))
        if full and full[1] and bad / n <= full[0] / full[1]:
            retire.append(f"`{rule}` ({model}, {effort}: 지운 변형 {bad}/{n}, 원래 {full[0]}/{full[1]})")
    out += ["", "은퇴 후보(규칙 문장을 지워도 위반이 늘지 않음): " + (", ".join(retire) or "없음")]

    recommend = []
    for model in sorted({k[0] for k in runs}):
        total = {}
        for (m, e, v, rule), (bad, n) in rates.items():
            if m == model and v == "full":
                t = total.setdefault(e, [0, 0])
                t[0] += bad
                t[1] += n
        scored = {e: t[0] / t[1] for e, t in total.items() if t[1]}
        if len(scored) < 2:
            continue
        best = min(scored.values())
        pick = min((e for e, r in scored.items() if r <= best), key=effort_key)
        recommend.append(f"{model}: `{pick}` (강도별 전체 위반률 "
                         + ", ".join(f"{e} {scored[e]:.0%}" for e in sorted(scored, key=effort_key)) + ")")
    out += ["권장 추론 강도(위반률이 가장 낮은 값과 같은 강도 중 가장 낮은 것): "
            + ("; ".join(recommend) or "강도를 둘 이상 돌린 모델 없음")]
    return "\n".join(out) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", required=True)
    a = p.parse_args(argv)
    sys.stdout.write(report(load(a.csv)))


if __name__ == "__main__":
    main()
