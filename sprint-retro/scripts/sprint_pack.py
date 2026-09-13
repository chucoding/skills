#!/usr/bin/env python3
"""스프린트 회고용 데이터 팩 — 지난 스프린트도 재수집해서 숫자를 뽑는다.

    python3 sprint_pack.py --list                     # 보드의 닫힌 스프린트 목록
    python3 sprint_pack.py --sprint 26_3_#4           # 그 스프린트 재수집 → 팩 생성
    python3 sprint_pack.py --current                  # 폴러가 만든 results.json 을 그대로 씀
    python3 sprint_pack.py --sprint 26_3_#4 --out /tmp/pack

읽기 전용이다. Jira 에 쓰지 않고 폴러의 상태 폴더도 건드리지 않는다 —
재수집 결과는 `--out` 폴더(기본 ./retro-pack)에만 쓴다. `refresh.py` 는 부르지 않는다
(그쪽은 담당자·상태 동기화와 실적 기입을 한다).

sprint-worktime-report 플러그인의 `collect.py`·`compute.py` 를 그대로 재사용한다.
collect.collect() 는 활성 스프린트만 보므로, 아래 두 지점만 갈아끼워 지난 스프린트를 태운다.

  - search()        : 경로 A 의 openSprints() 질의를 `sprint = "<대상>"` 으로 바꾸고,
                      경로 B(QA reopen)·경로 D(미완료 전부)는 빈 목록으로 만든다.
                      회고는 **그 스프린트에 배정됐던 것**만 대상이기 때문이다.
  - _active_sprint(): state 와 무관하게 대상 스프린트를 찾아 준다. closed 스프린트는
                      state=="active" 가 아니라 원본 함수가 None 을 돌려주고,
                      그러면 collect() 가 스프린트 메타를 못 찾아 죽는다.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta


def plugin_scripts_dir():
    """sprint-worktime-report 의 scripts 폴더 — 설치본 중 가장 높은 버전을 고른다."""
    env = os.environ.get("WORKTIME_SCRIPTS_DIR")
    if env and os.path.isdir(env):
        return env
    home = os.path.expanduser("~/.claude/plugins")
    cache = os.path.join(home, "cache/homedot-cloud-plugin/homedot-cloud-devteam")
    cands = []
    if os.path.isdir(cache):
        for v in os.listdir(cache):
            p = os.path.join(cache, v, "skills/sprint-worktime-report/scripts")
            if os.path.isfile(os.path.join(p, "collect.py")):
                key = tuple(int(x) for x in re.findall(r"\d+", v)) or (0,)
                cands.append((key, p))
    mp = os.path.join(home, "marketplaces/homedot-cloud-plugin/homedot-cloud-devteam"
                            "/skills/sprint-worktime-report/scripts")
    if os.path.isfile(os.path.join(mp, "collect.py")):
        cands.append(((0,), mp))
    if not cands:
        sys.exit("sprint-worktime-report 플러그인을 찾지 못했습니다. "
                 "WORKTIME_SCRIPTS_DIR 로 scripts 경로를 지정하세요.")
    return max(cands)[1]


def load_config():
    """폴러 설정을 환경변수로 올린다 — collect.py 가 import 시점에 읽는다."""
    cfg = os.path.expanduser("~/.config/homedot-worktime/config.env")
    if not os.path.exists(cfg):
        sys.exit(f"설정 파일이 없습니다: {cfg} (homedot-cloud-devteam:setup 스킬로 먼저 설정)")
    for line in open(cfg, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def sprints(collect, state=None):
    """보드의 스프린트 목록 — state 는 active/closed/future 또는 None(전부)."""
    out, start = [], 0
    while True:
        params = {"startAt": start, "maxResults": 50}
        if state:
            params["state"] = state
        res = collect._call(f"/rest/agile/1.0/board/{collect.BOARD_ID}/sprint", params=params)
        vals = res.get("values") or []
        out += vals
        if res.get("isLast", True) or not vals:
            break
        start += len(vals)
    return out


def patch_for_sprint(collect, target):
    """collect 모듈을 대상 스프린트용으로 갈아끼운다. 찾은 스프린트 dict 를 돌려준다."""
    all_sprints = sprints(collect)
    # 같은 이름의 스프린트가 둘인 경우가 실재한다(실측: 26_3_#3 2건). 이름이 겹치면
    # --list 가 보여 주는 id 로 지목할 수 있어야 한다.
    if str(target).isdigit():
        found = [s for s in all_sprints if str(s.get("id")) == str(target)]
    else:
        found = [s for s in all_sprints if s.get("name") == target]
    if not found:
        names = [f"{s.get('id')} {s.get('name')}" for s in all_sprints][-10:]
        sys.exit(f"스프린트 '{target}' 을 보드 {collect.BOARD_ID} 에서 찾지 못했습니다. "
                 f"최근: {', '.join(names)}")
    if len(found) > 1:
        opts = ", ".join(f"{s['id']}({(s.get('startDate') or '')[:10]})" for s in found)
        sys.exit(f"이름이 '{target}' 인 스프린트가 {len(found)}건입니다. id 로 지정하세요: {opts}")
    sprint = found[0]
    sid = sprint["id"]

    orig_search = collect.search

    def search(jql, *a, **kw):
        if "openSprints()" in jql:
            return orig_search(
                f"project = {collect.PROJECT} AND assignee = {collect.ASSIGNEE_ID} "
                f"AND sprint = {sid} ORDER BY updated DESC", *a, **kw)
        # 경로 B(QA reopen)·경로 D(미완료 전부)는 '지금 열려 있는 일' 이라 회고 대상이 아니다.
        return []

    collect.search = search
    collect._active_sprint = lambda issue: next(
        (sp for sp in (issue.get("fields", {}).get(collect.SPRINT_FIELD) or [])
         if sp.get("id") == sid), None)
    return sprint


def _canonical_repo(slug):
    """설정의 저장소 이름이 옛 이름일 수 있다 — 리다이렉트를 따라 현재 이름으로 바꾼다.

    이걸 안 하면 옛 이름으로도 `gh pr list` 가 **rc 0 에 빈 목록**을 돌려준다(실측 2026-09-13:
    rabyss/homedot-hub-react → dev-rsquare/hd-cloud-client, PR 0건으로 조용히 집계됨).
    조회 실패가 아니라 '그 기간에 머지가 없었다' 로 보이는 게 이 함정의 위험한 점이다.
    """
    try:
        p = subprocess.run(["gh", "repo", "view", slug, "--json", "nameWithOwner",
                            "-q", ".nameWithOwner"], capture_output=True, text=True, timeout=60)
    except Exception:                                             # noqa: BLE001
        return slug
    name = (p.stdout or "").strip()
    return name if p.returncode == 0 and "/" in name else slug


def gh_merged_prs(start, end):
    """스프린트 구간에 머지된 내 PR — 설정의 저장소 목록을 저장소별로 센다."""
    spec = os.environ.get("WORKTIME_GITHUB_REPO", "")
    slugs = [r.split("=", 1)[0].strip() for r in spec.split(",") if r.strip()]
    repos, errors, rows = [], [], []
    for slug in slugs:
        canon = _canonical_repo(slug)
        if canon != slug:
            errors.append(f"{slug} → {canon} 으로 해석 (설정의 이름이 옛 이름)")
        if canon not in repos:
            repos.append(canon)
    for repo in repos:
        cmd = ["gh", "pr", "list", "--repo", repo, "--author", "@me", "--state", "merged",
               "--search", f"merged:{start}..{end}", "--limit", "200",
               "--json", "number,title,url,mergedAt,additions,deletions,changedFiles,headRefName"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except Exception as e:                                    # noqa: BLE001
            errors.append(f"{repo}: {e}")
            continue
        if p.returncode != 0:
            errors.append(f"{repo}: {p.stderr.strip()[:200]}")
            continue
        found = json.loads(p.stdout or "[]")
        if not found:
            errors.append(f"{repo}: 머지 0건 — 저장소 이름·기간·gh 계정을 확인할 것")
        for pr in found:
            pr["repo"] = repo
            pr["jira"] = (re.search(r"(HDIT|HOM)-\d+", pr["title"] + " " + pr["headRefName"],
                                    re.I) or [None])[0]
            rows.append(pr)
    return rows, errors


def display_end(end_iso):
    """스프린트의 **표시용 종료일** — 종료가 자정이면 전날이다.

    이 값을 회고 머리말과 PR 조회에 똑같이 쓴다. 안 맞추면 경계일이 두 스프린트에 겹쳐
    들어간다(실측: 26_3_#4 의 종료가 08-31T00:00 이라 08-31 05:45Z 머지된 PR #2211 이
    #4 에도 #5 에도 잡혔다). GitHub 의 `merged:` 범위는 UTC 기준이라 이 보정 뒤에도
    한국시간 오전 9시 이전 머지 몇 건은 앞 스프린트로 넘어갈 수 있다.
    """
    d = datetime.fromisoformat(end_iso)
    if (d.hour, d.minute, d.second) == (0, 0, 0):
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def h(sec):
    return round((sec or 0) / 3600, 1)


def summarize(res, prs, pr_errors):
    """results.json + PR 목록 → 회고 템플릿이 요구하는 숫자들."""
    iss = res["issues"]
    cap = res.get("capacity") or {}
    done = {"개발완료", "배포완료", "완료", "Done", "Closed", "release"}

    def sp(i):
        return i.get("jira_story_points") or 0

    qa = [i for i in iss if i.get("qa_key")]
    no_start = [i for i in iss if not i.get("start_first")]
    zero = [i for i in iss if not (i.get("work_in_sprint_biz_seconds") or 0)]
    reopened = [i for i in iss if (i.get("reopen_count") or 0) or (i.get("qa_reopen_count") or 0)]
    ticket_keys = {i["key"] for i in iss} | {i["qa_key"] for i in iss if i.get("qa_key")}
    orphan_prs = [p for p in prs if not p.get("jira") or p["jira"].upper() not in ticket_keys]
    by_hours = sorted(iss, key=lambda i: i.get("work_in_sprint_biz_seconds") or 0, reverse=True)

    return {
        "sprint": res.get("sprint"),
        "assignee": res.get("assignee"),
        "board": res.get("board_label"),
        "티켓": {
            "전체": len(iss),
            "완료": sum(1 for i in iss if i.get("status") in done),
            "QA_결함": len(qa),
            "QA_결함_시간": h(sum(i.get("work_in_sprint_biz_seconds") or 0 for i in qa)),
            # 머리말의 '설계 문서 N건' 후보 — 제목 접두사로 고른 것이라 **사람이 확인해야
            # 하는 값**이다. 접두사 없이 쓴 설계 문서는 여기 안 잡힌다.
            "문서_티켓_후보": [f"{i['key']} {i['summary']}" for i in iss
                          if re.match(r"\s*\[(WIKI|발표|설계)\]", i.get("summary") or "")],
        },
        "PR": {
            "머지": len(prs),
            "저장소별": {r: sum(1 for p in prs if p["repo"] == r) for r in {p["repo"] for p in prs}},
            # 티켓 키가 없거나, 있어도 이 스프린트 티켓 목록에 없는 PR.
            # 회고 5절의 "티켓 밖에 있던 작업" 후보다 — 릴리스 PR 도 여기 섞인다.
            "스프린트_티켓에_없는_PR": [f"{p['repo']}#{p['number']} {p['title']}"
                                for p in orphan_prs],
            "조회_실패": pr_errors,
        },
        "부하": {
            "실가동h": h(cap.get("union_biz_seconds")),
            "캐파h": h(cap.get("total_biz_seconds")),
            "가동률%": round(100 * (cap.get("union_biz_seconds") or 0)
                           / (cap.get("total_biz_seconds") or 1)),
            "평균_동시_진행": cap.get("wip_avg"),
            "티켓별_합h": h(cap.get("work_biz_seconds")),
            "휴가h": h(cap.get("leave_seconds")),
            "기준": cap.get("basis"),
        },
        "계획": {
            "계획_SP_합": round(sum(sp(i) for i in iss), 2),
            "SP_환산h": round(sum(sp(i) for i in iss) * 8, 1),
            "SP_빈_티켓": [i["key"] for i in iss if not sp(i)],
        },
        "기록_구멍": {
            "작업시간_0": [f"{i['key']} {i['status']}" for i in zero],
            "착수_기록_없음": [i["key"] for i in no_start],
            "로그로_대체": [i["key"] for i in iss if i.get("work_source") == "worklog"],
            # '개발중' 에 하루 넘게 방치돼 체류시간이 작업시간으로 잡힌 티켓 — 실적h 를 그대로
            # 믿으면 안 되는 행이다. 회고에 쓰기 전에 실제 소요를 사람이 확인한다.
            "장기_열림_의심": [f"{i['key']} {h(i.get('work_in_sprint_biz_seconds'))}h"
                          for i in iss if i.get("long_open")],
        },
        "챌린지_후보": [
            {
                "key": i["key"],
                "summary": i["summary"],
                "status": i.get("status"),
                "실적h": h(i.get("work_in_sprint_biz_seconds")),
                "reopen": (i.get("reopen_count") or 0) + (i.get("qa_reopen_count") or 0),
                # 방치된 체류가 실적으로 잡힌 행 — 시간 순으로 맨 위에 오므로 여기 같이 실어
                # 목록만 보고 '가장 큰 작업' 으로 오해하지 않게 한다.
                "장기열림": bool(i.get("long_open")),
                "qa": i.get("qa_key"),
                "pr": [f"{p['repo']}#{p['number']} +{p['additions']}/-{p['deletions']} "
                       f"{p['changedFiles']}파일"
                       for p in prs if (p.get("jira") or "").upper() == i["key"]],
            }
            for i in by_hours[:15]
        ],
        "reopen_있음": [f"{i['key']} x{(i.get('reopen_count') or 0) + (i.get('qa_reopen_count') or 0)}"
                      for i in reopened],
        "부록_티켓별_실적": [
            {"key": i["key"], "summary": i["summary"], "status": i.get("status"),
             "실적h": h(i.get("work_in_sprint_biz_seconds")), "sp": sp(i),
             "출처": i.get("work_source")}
            for i in by_hours
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sprint", help="대상 스프린트 이름 (예: 26_3_#4)")
    ap.add_argument("--current", action="store_true", help="폴러의 results.json 을 그대로 사용")
    ap.add_argument("--list", action="store_true", help="보드 스프린트 목록만 출력")
    ap.add_argument("--out", default="retro-pack", help="산출 폴더 (기본 ./retro-pack)")
    args = ap.parse_args()

    load_config()
    sys.path.insert(0, plugin_scripts_dir())
    import collect                                                # noqa: E402

    if args.list:
        for s in sprints(collect):
            print(f"{s.get('id'):>5}  {s.get('state','?'):7} {s.get('name',''):10} "
                  f"{(s.get('startDate') or '')[:10]} ~ {(s.get('endDate') or '')[:10]}")
        return

    os.makedirs(args.out, exist_ok=True)
    results_path = os.path.join(args.out, "results.json")

    if args.current:
        # 설정 파일의 값에 `~` 가 그대로 들어 있다 — 셸이 아니라 파이썬이 읽으므로 직접 편다.
        state = os.path.expanduser(os.environ.get("WORKTIME_STATE_DIR")
                                   or "~/.config/homedot-worktime/state")
        src = os.path.join(state, "results.json")
        if not os.path.exists(src):
            sys.exit(f"폴러 결과가 없습니다: {src}")
        res = json.load(open(src, encoding="utf-8"))
        print(f"폴러 결과 사용: {src} (스프린트 {res.get('sprint', {}).get('name')})")
    else:
        if not args.sprint:
            sys.exit("--sprint 또는 --current 중 하나가 필요합니다. 목록은 --list.")
        sprint = patch_for_sprint(collect, args.sprint)
        print(f"재수집: {sprint['name']} ({sprint.get('startDate','')[:10]} ~ "
              f"{sprint.get('endDate','')[:10]})")
        try:
            data = collect.collect()
        except collect.JiraError as e:
            # collect 는 '활성 스프린트' 를 못 찾았다고 말하지만, 여기서는 원인이 하나다 —
            # 그 스프린트에 이 담당자의 티켓이 한 건도 없다(같은 이름의 빈 쌍둥이 스프린트가
            # 실재한다: 26_3_#3 은 2077·2078 두 개이고 티켓은 한쪽에만 있다).
            if "활성 스프린트" in str(e):
                sys.exit(f"스프린트 {sprint['name']}(id {sprint['id']})에 "
                         f"{os.environ.get('WORKTIME_ASSIGNEE_NAME', '담당자')}의 티켓이 "
                         f"없습니다. --list 로 같은 이름의 다른 id 를 확인하세요.")
            raise
        inp = os.path.join(args.out, "input.json")
        json.dump(data, open(inp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        compute = os.path.join(plugin_scripts_dir(), "compute.py")
        p = subprocess.run([sys.executable, compute, inp, results_path],
                           capture_output=True, text=True)
        if p.returncode != 0:
            sys.exit(f"compute.py 실패:\n{p.stderr}")
        res = json.load(open(results_path, encoding="utf-8"))

    json.dump(res, open(results_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    sp_meta = res.get("sprint") or {}
    start = (sp_meta.get("start") or "")[:10]
    end = display_end(sp_meta["end"]) if sp_meta.get("end") else ""
    prs, pr_errors = gh_merged_prs(start, end) if start and end else ([], ["스프린트 구간 없음"])

    pack = summarize(res, prs, pr_errors)
    # 머리말에 그대로 쓸 기간 — PR 조회에 쓴 것과 같은 종료일이다.
    pack["기간"] = f"{start} ~ {end}"
    pack["prs"] = prs
    pack_path = os.path.join(args.out, "retro-pack.json")
    json.dump(pack, open(pack_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    view = {k: v for k, v in pack.items() if k not in ("prs", "부록_티켓별_실적", "챌린지_후보")}
    print(json.dumps(view, ensure_ascii=False, indent=1))
    print(f"\n팩: {pack_path}  (챌린지 후보·부록·PR 원본은 이 파일 안)")


if __name__ == "__main__":
    main()
