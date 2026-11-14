#!/usr/bin/env python3
"""AGENTS.md 보강 루프의 측정 기간 시작 판정.

직전 보강 티켓 키로 hd-cloud-client 에서 `AGENTS.md` 를 바꾼 머지 PR 을 찾아 그 머지 시각을 기간 시작으로 삼는다.
없으면(반영할 규칙이 없었거나 아직 머지 전) 위키 `measurements.csv` 마지막 행의 기간 종료부터 이어서 잰다.
기간 종료는 실행 시각이라 `measure.py --end` 기본값이 맡는다. 절차는 chucoding 플러그인 `agents-md-loop` 스킬의 SKILL.md 를 본다.

  python3 ~/.claude/skills/chucoding/skills/agents-md-loop/scripts/period.py \
      --prev-ticket HDIT-6654 --csv W/measurements.main.csv

출력(JSON 한 줄)
  start   기간 시작 ISO 시각
  basis   티켓 설명 「측정 기간」 절에 그대로 적는 근거 한 줄
  merged  기간 시작으로 쓴 머지 PR 목록(번호, 제목, 머지 시각)
  open    아직 머지 전인 같은 티켓의 AGENTS.md PR 번호. 있으면 티켓에 그 사실을 적는다
"""
import argparse
import csv
import json
import subprocess
import sys

DEFAULT_REPO = "dev-rsquare/hd-cloud-client"


def gh_prs(repo, ticket, state):
    """티켓 키가 제목에 든 PR 목록"""
    res = subprocess.run(
        ["gh", "pr", "list", "--repo", repo, "--state", state, "--limit", "50",
         "--search", f"{ticket} in:title", "--json", "number,title,mergedAt,files"],
        capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"gh pr list 실패: {res.stderr.strip()}")
    return json.loads(res.stdout or "[]")


def touches_agents_md(pr):
    """PR 이 저장소 어딘가의 AGENTS.md 를 바꿨는지"""
    return any(f["path"].split("/")[-1] == "AGENTS.md" for f in (pr.get("files") or []))


def last_period_end(csv_path):
    """measurements.csv 마지막 행의 period_end. 파일이 비었거나 칸이 비면 None"""
    with open(csv_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None, None
    last = rows[-1]
    return (last.get("period_end") or None), last


def decide(ticket, merged, opened, csv_path):
    """기간 시작과 근거. merged, opened 는 gh pr list 결과"""
    merged = [p for p in merged if p.get("mergedAt") and touches_agents_md(p)]
    open_nums = [p["number"] for p in opened if touches_agents_md(p)]
    if merged:
        # 같은 티켓으로 보강 PR 이 여럿이면 마지막 머지 뒤부터 잰다
        merged.sort(key=lambda p: p["mergedAt"])
        last = merged[-1]
        basis = f"{ticket} 보강 PR #{last['number']} 머지 시각({last['mergedAt']})부터"
        if len(merged) > 1:
            basis += f", 같은 티켓 보강 PR {', '.join('#' + str(p['number']) for p in merged)} 중 마지막"
        start = last["mergedAt"]
    else:
        end, row = last_period_end(csv_path)
        if not end:
            sys.exit(f"{ticket} 의 머지된 AGENTS.md PR 이 없고 {csv_path} 마지막 행의 period_end 도 비어 있다. 기간 시작을 --start 로 정해 준다")
        why = "아직 머지 전" if open_nums else "없음"
        basis = (f"{ticket} 보강 PR {why}. measurements.csv 마지막 행"
                 f"({row['sprint']}, {row['ticket']})의 기간 종료({end})에서 이어짐")
        start = end
    return dict(start=start, basis=basis,
                merged=[dict(number=p["number"], title=p["title"], mergedAt=p["mergedAt"]) for p in merged],
                open=open_nums)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prev-ticket", required=True, help="직전 보강 티켓 키. 첫 실행은 HDIT-6654")
    p.add_argument("--csv", required=True, help="위키 origin/main 의 measurements.csv 사본")
    p.add_argument("--repo", default=DEFAULT_REPO)
    a = p.parse_args(argv)
    out = decide(a.prev_ticket, gh_prs(a.repo, a.prev_ticket, "merged"), gh_prs(a.repo, a.prev_ticket, "open"), a.csv)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
