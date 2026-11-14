#!/usr/bin/env python3
"""AGENTS.md 보강 루프 측정의 수집 단계.

범위 PR 목록과 PR별 리뷰, 코멘트, diff, 커밋을 작업 폴더에 내려받는다.
집계는 같은 폴더를 `measure.py` 에 넘겨 한다. 절차는 chucoding 플러그인 `agents-md-loop` 스킬의 SKILL.md,
측정 정의는 위키 `homedot-hub/knowledge/standards/effect/measurement.md` 를 본다.

  python3 ~/.claude/skills/chucoding/skills/agents-md-loop/scripts/collect.py --work W --since 2026-11-16T00:00:00+09:00

작업 폴더 구성
  prs.json          gh pr list 결과(검색어로 거른 전체)
  nums.txt          범위 경로를 바꾼 PR 번호(제외 PR 은 measure.py 가 뺀다)
  raw/<n>.comments.json        PR 인라인 리뷰 코멘트
  raw/<n>.reviews.json         PR 리뷰(본문 포함)
  raw/<n>.issue-comments.json  PR 대화 코멘트
  raw/<n>.diff                 PR 전체 diff
  raw/<n>.meta.json            커밋 목록과 PR 본문

GitHub 에 남은 기록을 읽기만 하므로 같은 인자로 다시 돌려도 결과가 같다.
이미 받은 PR 은 건너뛰고, --refresh 를 주면 다시 받는다.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

DEFAULT_REPO = "dev-rsquare/hd-cloud-client"
DEFAULT_REVIEWER = "hyeonseok-suh"
# 측정 정의 v1 의 범위 경로. 경로 안에 `/payroll` 이 있거나 `src/pages/erp/` 로 시작하는 파일
DEFAULT_SCOPE_REGEX = r"/payroll|^src/pages/erp/"


class GhError(Exception):
    """gh 명령 실패"""


def gh(args, out_path=None):
    """gh 명령 실행, out_path 가 있으면 표준 출력을 파일로 저장"""
    res = subprocess.run(["gh", *args], capture_output=True, text=True)
    if res.returncode != 0:
        raise GhError(f"gh {' '.join(args)} 실패: {res.stderr.strip()}")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(res.stdout)
    return res.stdout


def paginate_json(endpoint):
    """--paginate 로 이어 붙은 JSON 배열들을 하나의 배열 문자열로 합침"""
    raw = gh(["api", "--paginate", "--slurp", endpoint])
    pages = json.loads(raw) if raw.strip() else []
    merged = [item for page in pages for item in page]
    return json.dumps(merged, ensure_ascii=False)


def search_date(since):
    """GitHub 검색 created:>= 에 넣을 날짜. 날짜 한정자는 UTC 기준이라 UTC 날짜에서 하루 앞당겨 기간 초반 PR 을 놓치지 않음"""
    t = dt.datetime.fromisoformat(since.replace("Z", "+00:00"))
    t = t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
    return (t.astimezone(dt.timezone.utc).date() - dt.timedelta(days=1)).isoformat()


def in_scope(pr, scope):
    """PR 이 바꾼 파일 중 하나라도 범위 경로에 들면 참"""
    return any(scope.search(f["path"]) for f in (pr.get("files") or []))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--work", required=True, help="작업 폴더. 없으면 만든다")
    p.add_argument("--since", required=True,
                   help="기간 시작(YYYY-MM-DD 또는 시간대를 붙인 ISO 시각). 검색은 넓게 하고 정확한 필터는 measure.py 가 한다")
    p.add_argument("--repo", default=DEFAULT_REPO)
    p.add_argument("--reviewer", default=DEFAULT_REVIEWER, help="reviewed-by 검색에 쓰는 리뷰어 계정")
    p.add_argument("--scope-regex", default=DEFAULT_SCOPE_REGEX, help="범위 파일 경로 정규식")
    p.add_argument("--limit", type=int, default=1000, help="gh pr list 최대 건수")
    p.add_argument("--exclude", default="", help="받지 않을 PR 번호, 쉼표 구분(승격과 통합 PR 처럼 diff 가 너무 큰 PR)")
    p.add_argument("--refresh", action="store_true", help="이미 받은 PR 도 다시 받는다")
    a = p.parse_args(argv)

    try:
        since = search_date(a.since)
    except ValueError:
        sys.exit("--since 는 YYYY-MM-DD 또는 ISO 시각이어야 한다")
    os.makedirs(os.path.join(a.work, "raw"), exist_ok=True)
    scope = re.compile(a.scope_regex)

    prs_path = os.path.join(a.work, "prs.json")
    try:
        gh([
            "pr", "list", "--repo", a.repo, "--state", "all",
            "--search", f"reviewed-by:{a.reviewer} created:>={since}",
            "--limit", str(a.limit),
            "--json", "number,title,createdAt,mergedAt,closedAt,state,author,additions,deletions,files,headRefName",
        ], prs_path)
    except GhError as e:
        sys.exit(str(e))
    with open(prs_path, encoding="utf-8") as f:
        prs = json.load(f)
    if len(prs) >= a.limit:
        print(f"경고: gh pr list 결과가 --limit {a.limit} 에 닿았다. 늘려서 다시 돌린다", file=sys.stderr)

    nums = sorted(pr["number"] for pr in prs if in_scope(pr, scope))
    with open(os.path.join(a.work, "nums.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(map(str, nums)) + ("\n" if nums else ""))

    exclude = {int(x) for x in a.exclude.split(",") if x.strip()}
    failed = []
    for n in nums:
        if n in exclude:
            continue
        base = os.path.join(a.work, "raw", str(n))
        targets = {
            f"{base}.comments.json": lambda: paginate_json(f"repos/{a.repo}/pulls/{n}/comments"),
            f"{base}.reviews.json": lambda: paginate_json(f"repos/{a.repo}/pulls/{n}/reviews"),
            f"{base}.issue-comments.json": lambda: paginate_json(f"repos/{a.repo}/issues/{n}/comments"),
            f"{base}.diff": lambda: gh(["pr", "diff", str(n), "--repo", a.repo]),
            f"{base}.meta.json": lambda: gh(["pr", "view", str(n), "--repo", a.repo, "--json", "commits,body"]),
        }
        for path, fetch in targets.items():
            if os.path.exists(path) and not a.refresh:
                continue
            try:
                text = fetch()
            except GhError as e:
                # diff 가 GitHub 한도(파일 300개)를 넘는 PR 등. 실패를 남기고 다음으로 간다
                with open(f"{path}.error", "w", encoding="utf-8") as f:
                    f.write(str(e) + "\n")
                failed.append(f"{os.path.basename(path)}: {e}")
                continue
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            if os.path.exists(f"{path}.error"):
                # 다시 받는 데 성공했으면 지난 실패 기록을 지운다. measure.py 가 .error 로 수집 실패를 판정한다
                os.remove(f"{path}.error")
    for line in failed:
        print(f"경고: {line}", file=sys.stderr)
    print(f"검색 PR {len(prs)}건, 범위 PR {len(nums)}건 → {a.work}")


if __name__ == "__main__":
    main()
