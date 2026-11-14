#!/usr/bin/env python3
"""AGENTS.md 회귀 프롬프트 실행기.

`tasks/*.json` 과제마다 hd-cloud-client 임시 git worktree 를 과제의 base 커밋으로 만들고, 지금 `AGENTS.md`
(기본 origin/main) 를 덮어쓴 뒤 `claude -p` 로 과제를 돌린다. 끝나면 변경을 채점(grade.py)하고 worktree 를 지운다.
조합은 과제 × 모델 × 추론 강도 × 변형(full, stripped) × 반복이다. 절차는 chucoding 플러그인 `agents-md-regress` 스킬의 SKILL.md 를 본다.

  # 조합 수와 예상 비용만 출력(실행하지 않음)
  python3 run.py --out W --model claude-opus-5-5 --effort low --effort medium --repeat 3 --plan
  # 실행. --yes 가 없으면 계획만 보여 주고 멈춘다
  python3 run.py --out W --task fsd04-2860 --model claude-opus-5-5 --effort low --repeat 1 --yes

출력
  W/runs.csv     규칙 ID별 한 행(regression-runs.csv 칸). 위키에 넘길 행이다
  W/runs.jsonl   실행 한 번에 한 줄(claude 결과 요약, diff 경로, 채점 근거)
  W/diffs/<run_id>.diff  채점한 diff
"""
import argparse
import csv
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import grade  # noqa: E402

DEFAULT_REPO = "/Users/hyeonseoksuh/homedot/hd-cloud-client"
TASKS_DIR = os.path.join(HERE, "..", "tasks")
RUN_FIELDS = ["run_at", "run_id", "task", "source_pr", "base_commit", "agents_md_ref", "agents_md_sha", "variant",
              "model", "effort", "repeat", "rule_id", "method", "violations", "is_error", "input_tokens",
              "output_tokens", "cache_read_tokens", "cache_creation_tokens", "duration_s", "cost_usd",
              "judge_model", "judge_effort", "judge_cost_usd", "no_change"]
TIMEOUT_S = 1800


def git(repo, *args, check=True, text=True):
    """git 실행. 실패하면 stderr 와 함께 멈춤"""
    res = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=text)
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패: {res.stderr.strip() if text else res.stderr}")
    return res


def load_tasks(ids):
    """과제 파일 목록. ids 가 비면 전부"""
    names = sorted(f[:-5] for f in os.listdir(TASKS_DIR) if f.endswith(".json"))
    pick = ids or names
    unknown = [i for i in pick if i not in names]
    if unknown:
        sys.exit(f"없는 과제: {', '.join(unknown)} (있는 것: {', '.join(names)})")
    return [json.load(open(os.path.join(TASKS_DIR, f"{i}.json"), encoding="utf-8")) for i in pick]


def strip_rules(text, needles):
    """needles 중 하나라도 든 줄을 지운 AGENTS.md 와, 어느 줄에도 걸리지 않은 needle 목록.
    하나라도 안 걸리면 규칙 문장이 남은 채 비교군이 되어 가짜 은퇴 후보가 생기므로 호출 쪽이 멈춘다"""
    lines = text.splitlines(keepends=True)
    kept = [ln for ln in lines if not any(n in ln for n in needles)]
    unmatched = [n for n in needles if not any(n in ln for ln in lines)]
    return "".join(kept), unmatched


def prepare_worktree(repo, wt, task, agents_md, variant):
    """base 커밋으로 worktree 를 만들고 AGENTS.md 를 덮어씀. 덮어쓴 상태를 커밋해 채점 diff 에서 빠지게 함"""
    git(repo, "worktree", "add", "--detach", wt, task["base_commit"])
    text = agents_md
    if variant == "stripped":
        text, unmatched = strip_rules(agents_md, task.get("agents_md_strip") or [])
        if unmatched:
            raise RuntimeError(f"{task['id']}: agents_md_strip 문자열이 AGENTS.md 에 없다: {unmatched}")
    with open(os.path.join(wt, "AGENTS.md"), "w", encoding="utf-8") as f:
        f.write(text)
    if not os.path.exists(os.path.join(wt, "CLAUDE.md")):
        # 이 저장소 CLAUDE.md 는 AGENTS.md 를 가져오기만 한다. base 커밋에 없으면 같은 내용으로 둔다
        with open(os.path.join(wt, "CLAUDE.md"), "w", encoding="utf-8") as f:
            f.write("@AGENTS.md\n")
    git(wt, "add", "-A")
    git(wt, "-c", "user.name=agents-md-regress", "-c", "user.email=agents-md-regress@local",
        "commit", "-q", "--no-verify", "--allow-empty", "-m", f"regress: {variant} AGENTS.md")
    return git(wt, "rev-parse", "HEAD").stdout.strip()


def run_claude(wt, prompt, model, effort, budget):
    """claude -p 한 번. 사용자 설정(플러그인, 훅)을 읽지 않게 project, local 설정만 쓴다"""
    cmd = ["claude", "-p", prompt, "--model", model, "--effort", effort, "--output-format", "json",
           "--permission-mode", "acceptEdits", "--max-budget-usd", str(budget),
           "--no-session-persistence", "--setting-sources", "project,local"]
    try:
        res = subprocess.run(cmd, cwd=wt, capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"is_error": True, "subtype": "timeout"}
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return {"is_error": True, "subtype": "unparsable", "stderr": res.stderr[-2000:], "stdout": res.stdout[-2000:]}


def changed_diff(wt, base):
    """에이전트가 바꾼 내용(새 파일 포함). AGENTS.md 덮어쓰기 커밋 이후만"""
    git(wt, "add", "-A")
    return git(wt, "diff", "--cached", base, "--", ".", ":(exclude)AGENTS.md", ":(exclude)CLAUDE.md").stdout


def remove_worktree(repo, wt):
    """임시 worktree 만 지움. 사용자 메인 체크아웃과 다른 worktree 는 건드리지 않음"""
    git(repo, "worktree", "remove", "--force", wt, check=False)
    if os.path.exists(wt):
        shutil.rmtree(wt, ignore_errors=True)
    git(repo, "worktree", "prune", check=False)


def plan(tasks, models, efforts, variants, repeat, budget):
    """조합 수와 상한 비용"""
    runs = []
    for t in tasks:
        for v in variants:
            if v == "stripped" and not t.get("agents_md_strip"):
                continue
            for m in models:
                for e in efforts:
                    for r in range(1, repeat + 1):
                        runs.append((t, v, m, e, r))
    judge_calls = sum(len(t["grading"].get("judge") or []) for t, *_ in runs)
    return runs, judge_calls, len(runs) * budget


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, help="결과 폴더")
    p.add_argument("--repo", default=DEFAULT_REPO, help="hd-cloud-client 클론(임시 worktree 를 여기서 만든다)")
    p.add_argument("--task", action="append", default=[], help="과제 id. 비우면 tasks/ 전부")
    p.add_argument("--model", action="append", required=True)
    p.add_argument("--effort", action="append", required=True, help="low, medium, high 등")
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--variant", action="append", choices=["full", "stripped"], default=[],
                   help="full=지금 AGENTS.md, stripped=과제 규칙 문장을 지운 AGENTS.md(은퇴 판단용). 기본 full")
    p.add_argument("--agents-md-ref", default="origin/main", help="덮어쓸 AGENTS.md 를 읽을 hd-cloud-client ref")
    p.add_argument("--budget-usd", type=float, default=3.0, help="실행 한 번의 상한(--max-budget-usd)")
    p.add_argument("--plan", action="store_true", help="조합과 예상 비용만 출력")
    p.add_argument("--yes", action="store_true", help="계획을 승인받았으면 붙인다. 없으면 실행하지 않는다")
    a = p.parse_args(argv)

    tasks = load_tasks(a.task)
    variants = a.variant or ["full"]
    runs, judge_calls, cap = plan(tasks, a.model, a.effort, variants, a.repeat, a.budget_usd)
    print(f"조합 {len(runs)}회(과제 {len(tasks)} × 모델 {len(a.model)} × 강도 {len(a.effort)} × 변형 {len(variants)} × 반복 {a.repeat}),"
          f" 채점 프롬프트 {judge_calls}회, 실행 비용 상한 ${cap:.2f}(실행당 ${a.budget_usd:.2f})", file=sys.stderr)
    # 유료 실행 전에 비교군 문장과 채점 규칙 절을 먼저 확인한다. 어긋나면 계획 단계에서 멈춘다
    git(a.repo, "fetch", "-q", "origin", a.agents_md_ref.split("/", 1)[-1], check=False)
    agents_md = git(a.repo, "show", f"{a.agents_md_ref}:AGENTS.md").stdout
    problems = []
    if "stripped" in variants:
        for t in tasks:
            _, unmatched = strip_rules(agents_md, t.get("agents_md_strip") or [])
            if unmatched:
                problems.append(f"{t['id']}: agents_md_strip 이 {a.agents_md_ref} AGENTS.md 에 없음 {unmatched}")
    problems += grade.check_tasks(tasks)
    if problems:
        sys.exit("실행 전 확인 실패:\n" + "\n".join(problems))
    if a.plan or not a.yes:
        if not a.plan:
            print("--yes 가 없어 실행하지 않았다. 계획을 승인받은 뒤 --yes 를 붙인다", file=sys.stderr)
        return

    agents_sha = git(a.repo, "rev-parse", a.agents_md_ref).stdout.strip()
    os.makedirs(os.path.join(a.out, "diffs"), exist_ok=True)
    # ~/.claude 아래는 Claude Code 가 보호 경로로 보고 편집을 거부한다(2026-11-15 실측: 16턴 동안 diff 0줄).
    # 그래서 결과는 --out 에 두고 worktree 는 시스템 임시 폴더에 만든다
    wt_root = tempfile.mkdtemp(prefix="agents-md-regress-")
    csv_path = os.path.join(a.out, "runs.csv")
    new_csv = not os.path.exists(csv_path)
    if not new_csv:
        with open(csv_path, encoding="utf-8", newline="") as f:
            header = next(csv.reader(f), [])
        if header != RUN_FIELDS:
            # 칸이 바뀐 이전 버전 파일에 이어 쓰면 행이 헤더와 어긋나 새 칸 값이 사라진다
            sys.exit(f"{csv_path} 의 칸이 지금 실행기와 다르다. 다른 --out 폴더를 쓴다")
    with open(csv_path, "a", encoding="utf-8", newline="") as cf, open(os.path.join(a.out, "runs.jsonl"), "a", encoding="utf-8") as jf:
        w = csv.DictWriter(cf, RUN_FIELDS, lineterminator="\n")
        if new_csv:
            w.writeheader()
        for t, variant, model, effort, rep in runs:
            run_id = f"{t['id']}-{variant}-{effort}-{rep}-{uuid.uuid4().hex[:6]}"
            wt = os.path.join(wt_root, run_id)
            started = dt.datetime.now().astimezone()
            try:
                base = prepare_worktree(a.repo, wt, t, agents_md, variant)
                out = run_claude(wt, t["prompt"], model, effort, a.budget_usd)
                diff = changed_diff(wt, base)
            finally:
                remove_worktree(a.repo, wt)
            if not diff.strip():
                denials = len(out.get("permission_denials") or [])
                print(f"경고: {run_id} 변경 없음(권한 거부 {denials}건). runs.jsonl 의 result 와 permission_denials 를 본다",
                      file=sys.stderr)
            diff_path = os.path.join(a.out, "diffs", f"{run_id}.diff")
            with open(diff_path, "w", encoding="utf-8") as f:
                f.write(diff)
            try:
                scores = grade.grade(t, diff, wiki=grade.DEFAULT_WIKI)
            except ValueError:   # 과제 설정 오류는 check_tasks 가 먼저 막는다. 여기서 나면 숨기지 않고 멈춘다
                raise
            except Exception as e:   # 이미 비용을 쓴 실행이라 행은 남기고 다음 조합으로 간다
                scores = grade.error_scores(t, e)
            usage = out.get("usage") or {}
            base_row = dict(run_at=started.isoformat(timespec="seconds"), run_id=run_id, task=t["id"],
                            source_pr=t.get("source_pr", ""), base_commit=t["base_commit"],
                            agents_md_ref=a.agents_md_ref, agents_md_sha=agents_sha, variant=variant,
                            model=model, effort=effort, repeat=rep, is_error=bool(out.get("is_error")),
                            input_tokens=usage.get("input_tokens", ""), output_tokens=usage.get("output_tokens", ""),
                            cache_read_tokens=usage.get("cache_read_input_tokens", ""),
                            cache_creation_tokens=usage.get("cache_creation_input_tokens", ""),
                            duration_s=round((out.get("duration_ms") or 0) / 1000, 1),
                            cost_usd=out.get("total_cost_usd", ""), no_change=not diff.strip())
            for s in scores:
                w.writerow({**base_row, "rule_id": s["rule_id"], "method": s["method"], "violations": s["violations"],
                            "judge_model": s.get("judge_model", ""), "judge_effort": s.get("judge_effort", ""),
                            "judge_cost_usd": s.get("judge_cost_usd", "")})
            jf.write(json.dumps(dict(run_id=run_id, task=t["id"], variant=variant, model=model, effort=effort,
                                     repeat=rep, diff=diff_path, diff_lines=diff.count("\n"), scores=scores,
                                     result={k: out.get(k) for k in ("subtype", "is_error", "num_turns", "duration_ms",
                                                                     "total_cost_usd", "usage", "stderr",
                                                                     "permission_denials", "result")}),
                                ensure_ascii=False) + "\n")
            cf.flush()
            jf.flush()
            judge_cost = sum(s.get("judge_cost_usd") or 0 for s in scores)
            failed = sum(1 for s in scores if s["violations"] is None)
            print(f"{run_id}: 위반 {sum(s['violations'] or 0 for s in scores)}건, 채점 실패 {failed}건, 비용 ${out.get('total_cost_usd', 0) or 0:.3f}"
                  f"(채점 ${judge_cost:.3f}), diff {diff.count(chr(10))}줄, 오류 {bool(out.get('is_error'))}", file=sys.stderr)
    shutil.rmtree(wt_root, ignore_errors=True)


if __name__ == "__main__":
    main()
