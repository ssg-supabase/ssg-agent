"""ssg-agent 명령어 (M1 뼈대). 관리자 화면이 생기기 전까지 이걸로 기록을 만들고 확인합니다.

자주 쓰는 명령:
  python ssg.py init "내 작업공간"
  python ssg.py channel add book "밑줄 그은 하루" --genres book,self_help
  python ssg.py channel list
  python ssg.py channel setup book                 # 유튜브 시작 도우미 체크리스트
  python ssg.py channel check book phone_verify    # 체크리스트 항목 완료 표시
  python ssg.py project new book "잠잘 때 손해 보는 습관" --genre book
  python ssg.py project list
  python ssg.py project show p0001
  python ssg.py project upload p0001 그림.png --purpose ref_image --rights
  python ssg.py project level p0001 2              # 자동화 수준 바꾸기
  python ssg.py project step p0001 brief running   # (테스트용) 단계 상태 바꾸기
  python ssg.py genres
  python ssg.py providers
  python ssg.py providers set tts tts.upload       # 역할 담당 AI 바꾸기
  python ssg.py user list                          # 사용자 (관리자는 .env 의 ADMIN_EMAIL 로 자동 생성)
  python ssg.py user add a@b.com --role editor --channels book
  python ssg.py user access a@b.com --channel faith on
  python ssg.py user access a@b.com --project p0003 off
  python ssg.py user set a@b.com --status suspended
"""
import argparse
import getpass
import sys

from dotenv import load_dotenv

from core import genres as genre_lib
from core import providers
from core.models import (
    AUTOMATION_LEVELS, STATUS_LABELS, STEP_LABELS, STEPS, UPLOAD_PURPOSES, YOUTUBE_SETUP_ITEMS,
)
from core import users as user_lib
from core.store import Store
from core.users import Users

LEVEL_NAMES = {0: "전부 확인", 1: "기획 확인", 2: "최종만 확인", 3: "완전 자동"}


def cmd_init(store, a):
    ws = store.init_workspace(a.name)
    print(f"작업공간을 만들었습니다: {ws.name} ({store.root}/)")
    admin = Users(store.root).seed_admin_from_env()
    if admin:
        print(f"전체 관리자 계정을 만들었습니다: {admin['id']} (.env 의 ADMIN_EMAIL)")
    else:
        print("참고: .env 에 ADMIN_EMAIL · ADMIN_PASSWORD 를 넣고 `python ssg.py user seed` 하면 관리자 계정이 생깁니다.")
    print("다음: python ssg.py channel add book \"채널 이름\" --genres book,self_help")


def cmd_channel_add(store, a):
    known = genre_lib.list_genres(store.root)
    genres = [g for g in (a.genres or "").split(",") if g]
    unknown = [g for g in genres if g not in known]
    if unknown:
        sys.exit(f"모르는 장르: {', '.join(unknown)} (선택지: {', '.join(known)})")
    ch = store.add_channel(a.id, a.name, genres)
    print(f"채널을 만들었습니다: {ch.name} [{ch.id}] 장르: {', '.join(genres) or '없음'}")


def cmd_channel_list(store, a):
    channels = store.list_channels()
    if not channels:
        print("채널이 없습니다.")
    for ch in channels:
        done = sum(ch.youtube_setup.values())
        n = len(store.list_projects(ch.id))
        print(f"[{ch.id}] {ch.name}  장르: {', '.join(ch.genres)}  프로젝트 {n}개  유튜브 설정 {done}/{len(ch.youtube_setup)}")


def cmd_channel_setup(store, a):
    ch = store.load_channel(a.id)
    print(f"유튜브 시작 도우미 — {ch.name}")
    for i, (key, label) in enumerate(YOUTUBE_SETUP_ITEMS, 1):
        mark = "✓" if ch.youtube_setup.get(key) else " "
        print(f"  [{mark}] {i:2}. {label}  ({key})")
    print("\n완료 표시: python ssg.py channel check", ch.id, "<항목키>")


def cmd_channel_check(store, a):
    ch = store.load_channel(a.id)
    if a.item not in dict(YOUTUBE_SETUP_ITEMS):
        sys.exit(f"모르는 항목입니다: {a.item}")
    ch.youtube_setup[a.item] = not a.undo
    store.save_channel(ch)
    print(f"{dict(YOUTUBE_SETUP_ITEMS)[a.item]}: {'완료' if not a.undo else '미완료'}")


def cmd_project_new(store, a):
    overrides = {"aspect": a.aspect, "length_sec": a.length, "art_style": a.style, "voice_mode": a.voice}
    if a.genre:
        g = genre_lib.load(a.genre, store.root)
        overrides["genre"] = a.genre
        if a.length is None:
            overrides["length_sec"] = g["length_sec"]["default"]
    p = store.new_project(a.channel, a.topic, a.title or "", **overrides)
    if a.level is not None:
        p.apply_automation_level(a.level)
        store.save_project(p)
    print(f"프로젝트를 만들었습니다: {p.id} {p.title}")
    print(f"폴더: {store.project_dir(p)}")


def cmd_project_list(store, a):
    projects = store.list_projects(a.channel)
    if not projects:
        print("프로젝트가 없습니다.")
    for p in projects:
        current = next((STEP_LABELS[k] + " · " + STATUS_LABELS[s["status"]]
                        for k, s in p.steps.items() if s["status"] not in ("done", "skipped")), "모두 완료")
        print(f"{p.id}  [{p.channel_id}] {p.title}  — {current}")


def cmd_project_show(store, a):
    p = store.load_project(a.id)
    s = p.spec
    print(f"{p.id}  {p.title}")
    print(f"  채널 {p.channel_id} · 장르 {s['genre'] or '-'} · {s['aspect']} {s['width']}x{s['height']} · "
          f"{s['length_sec']}초 · 그림체 {s['art_style'] or '미정'} · 목소리 {s['voice_mode']} · 품질 {s['quality']}")
    print(f"  자동화 레벨 {p.automation_level} ({LEVEL_NAMES[p.automation_level]}) · 비용 ${p.cost_total_usd}")
    print(f"  폴더: {store.project_dir(p)}")
    print("  단계:")
    for i, (key, label) in enumerate(STEPS, 1):
        st = p.steps[key]
        stop = " ⏸" if st["needs_approval"] else ""
        err = f"  ← {st['error']}" if st["error"] else ""
        print(f"    {i:2}. {label:<12} {STATUS_LABELS[st['status']]}{stop}{err}")
    if p.uploads:
        print("  올린 자료:")
        for u in p.uploads:
            ok = "" if u["rights_confirmed"] else "  (권리 확인 안 됨)"
            print(f"    {u['id']} {UPLOAD_PURPOSES[u['purpose']]}: {u['filename']}{ok}")


def cmd_project_upload(store, a):
    p = store.load_project(a.id)
    u = store.add_upload(p, a.file, a.purpose, rights_confirmed=a.rights, note=a.note or "")
    print(f"올렸습니다: {u.id} [{UPLOAD_PURPOSES[u.purpose]}] {u.filename}")
    if not a.rights:
        print("  참고: 사용 권리를 확인했다면 --rights 를 붙이세요. 확인 안 된 자료는 렌더링 전에 경고합니다.")


def cmd_project_level(store, a):
    p = store.load_project(a.id)
    p.apply_automation_level(a.level)
    store.save_project(p)
    stops = [STEP_LABELS[k] for k, _ in STEPS if k in AUTOMATION_LEVELS[a.level]]
    print(f"{p.id} 자동화 레벨 {a.level} ({LEVEL_NAMES[a.level]}) — 멈추는 단계: {', '.join(stops) or '없음'}")


def cmd_project_step(store, a):
    p = store.load_project(a.id)
    step = store.update_step(p, a.step, a.status, error=a.error or "")
    print(f"{p.id} {STEP_LABELS[a.step]} → {STATUS_LABELS[step.status]}")


def cmd_genres(store, a):
    for gid, g in genre_lib.list_genres(store.root).items():
        L = g["length_sec"]
        print(f"[{gid}] {g['name']}  {L['min']}~{L['max']}초  구조: {' → '.join(g['structure'])}")


def cmd_providers(store, a):
    settings = store.load_workspace().providers if store.exists() else {}
    for role, label in providers.ROLES.items():
        current = providers.get(role, settings)
        options = providers.for_role(role)
        if current:
            ok, why = current.ready()
            state = f"{current.label} ({current.id}) — {'●' if ok else '○'} {why}"
        else:
            state = "미지정"
        others = [p.id for p in options if p is not current]
        alt = f"   다른 선택지: {', '.join(others)}" if others else ""
        print(f"{label:<10} {state}{alt}")


def cmd_providers_set(store, a):
    ws = store.load_workspace()
    providers.assign(ws.providers, a.role, a.provider)
    store.save_workspace(ws)
    print(f"{providers.ROLES[a.role]} 담당 → {a.provider}")


def cmd_user_list(store, a):
    for u in Users(store.root).all():
        chans = "전체" if u["role"] == "admin" else ", ".join(c for c, on in u["channels"].items() if on) or "없음"
        extra = "".join([" · 재설정 요청" if u["reset_requested"] else "", " · 비밀번호 변경 필요" if u["must_change"] else ""])
        print(f"{u['id']}  {u['name']}  {user_lib.ROLES[u['role']]}  {user_lib.STATUSES[u['status']]}  채널: {chans}{extra}")


def cmd_user_seed(store, a):
    u = Users(store.root).seed_admin_from_env()
    print(f"전체 관리자 계정을 만들었습니다: {u['id']}" if u else
          "만들지 않았습니다 (이미 사용자가 있거나 .env 에 ADMIN_EMAIL · ADMIN_PASSWORD 가 없음).")


def cmd_user_add(store, a):
    pw = getpass.getpass("임시 비밀번호 (8자 이상): ")
    u = Users(store.root).add(a.id, pw, a.role, a.name or "", (a.channels or "").split(",") if a.channels else [])
    print(f"등록했습니다: {u['id']} ({user_lib.ROLES[u['role']]}) — 첫 로그인 때 비밀번호를 바꾸게 됩니다.")


def cmd_user_set(store, a):
    fields = {k: v for k, v in (("name", a.name), ("role", a.role), ("status", a.status)) if v}
    u = Users(store.root).update(a.id, **fields)
    print(f"{u['id']}: {user_lib.ROLES[u['role']]} · {user_lib.STATUSES[u['status']]}")


def cmd_user_access(store, a):
    users = Users(store.root)
    if a.project:
        users.set_project(a.id, a.project, a.mode)
        print(f"{a.id} 프로젝트 {a.project}: {a.mode}")
    else:
        if a.mode == "inherit":
            sys.exit("채널은 on 또는 off 만 됩니다.")
        users.set_channel(a.id, a.channel, a.mode == "on")
        print(f"{a.id} 채널 {a.channel}: {a.mode}")


def cmd_user_temp(store, a):
    print(f"임시 비밀번호: {Users(store.root).issue_temp_password(a.id)}  (지금 한 번만 보입니다)")


def cmd_user_passwd(store, a):
    cur = getpass.getpass("현재 비밀번호: ")
    new = getpass.getpass("새 비밀번호 (8자 이상): ")
    if new != getpass.getpass("새 비밀번호 확인: "):
        sys.exit("오류: 새 비밀번호 확인이 다릅니다.")
    Users(store.root).change_password(a.id, cur, new)
    print("비밀번호를 바꿨습니다.")


def cmd_user_delete(store, a):
    Users(store.root).delete(a.id)
    print(f"삭제했습니다: {a.id}")


def build_parser():
    ap = argparse.ArgumentParser(prog="ssg.py", description="ssg-agent 쇼츠 자동화 (M1)")
    ap.add_argument("--root", default="workspace", help="작업공간 폴더 (기본: workspace)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="작업공간 만들기"); p.add_argument("name"); p.set_defaults(fn=cmd_init)

    ch = sub.add_parser("channel", help="채널").add_subparsers(dest="sub", required=True)
    p = ch.add_parser("add"); p.add_argument("id"); p.add_argument("name"); p.add_argument("--genres")
    p.set_defaults(fn=cmd_channel_add)
    ch.add_parser("list").set_defaults(fn=cmd_channel_list)
    p = ch.add_parser("setup"); p.add_argument("id"); p.set_defaults(fn=cmd_channel_setup)
    p = ch.add_parser("check"); p.add_argument("id"); p.add_argument("item")
    p.add_argument("--undo", action="store_true"); p.set_defaults(fn=cmd_channel_check)

    pr = sub.add_parser("project", help="프로젝트").add_subparsers(dest="sub", required=True)
    p = pr.add_parser("new"); p.add_argument("channel"); p.add_argument("topic")
    p.add_argument("--title"); p.add_argument("--genre"); p.add_argument("--aspect", choices=["9:16", "1:1", "4:5", "16:9"])
    p.add_argument("--length", type=int); p.add_argument("--style"); p.add_argument("--voice", choices=["ai", "my_recording", "mixed"])
    p.add_argument("--level", type=int, choices=[0, 1, 2, 3]); p.set_defaults(fn=cmd_project_new)
    p = pr.add_parser("list"); p.add_argument("--channel"); p.set_defaults(fn=cmd_project_list)
    p = pr.add_parser("show"); p.add_argument("id"); p.set_defaults(fn=cmd_project_show)
    p = pr.add_parser("upload"); p.add_argument("id"); p.add_argument("file")
    p.add_argument("--purpose", required=True, choices=list(UPLOAD_PURPOSES))
    p.add_argument("--rights", action="store_true"); p.add_argument("--note"); p.set_defaults(fn=cmd_project_upload)
    p = pr.add_parser("level"); p.add_argument("id"); p.add_argument("level", type=int, choices=[0, 1, 2, 3])
    p.set_defaults(fn=cmd_project_level)
    p = pr.add_parser("step"); p.add_argument("id"); p.add_argument("step", choices=list(STEP_LABELS))
    p.add_argument("status", choices=list(STATUS_LABELS)); p.add_argument("--error"); p.set_defaults(fn=cmd_project_step)

    sub.add_parser("genres", help="장르 템플릿 보기").set_defaults(fn=cmd_genres)
    pv = sub.add_parser("providers", help="AI 연결 상태")
    pv.set_defaults(fn=cmd_providers)
    pvs = pv.add_subparsers(dest="sub")
    p = pvs.add_parser("set"); p.add_argument("role"); p.add_argument("provider"); p.set_defaults(fn=cmd_providers_set)

    us = sub.add_parser("user", help="사용자·권한").add_subparsers(dest="sub", required=True)
    us.add_parser("list").set_defaults(fn=cmd_user_list)
    us.add_parser("seed", help=".env 로 전체 관리자 만들기").set_defaults(fn=cmd_user_seed)
    p = us.add_parser("add"); p.add_argument("id"); p.add_argument("--name")
    p.add_argument("--role", default="editor", choices=list(user_lib.ROLES)); p.add_argument("--channels")
    p.set_defaults(fn=cmd_user_add)
    p = us.add_parser("set"); p.add_argument("id"); p.add_argument("--name")
    p.add_argument("--role", choices=list(user_lib.ROLES)); p.add_argument("--status", choices=list(user_lib.STATUSES))
    p.set_defaults(fn=cmd_user_set)
    p = us.add_parser("access", help="채널/프로젝트 접근 on·off"); p.add_argument("id")
    g = p.add_mutually_exclusive_group(required=True); g.add_argument("--channel"); g.add_argument("--project")
    p.add_argument("mode", choices=["on", "off", "inherit"]); p.set_defaults(fn=cmd_user_access)
    p = us.add_parser("temp", help="임시 비밀번호 발급"); p.add_argument("id"); p.set_defaults(fn=cmd_user_temp)
    p = us.add_parser("passwd", help="비밀번호 변경"); p.add_argument("id"); p.set_defaults(fn=cmd_user_passwd)
    p = us.add_parser("delete"); p.add_argument("id"); p.set_defaults(fn=cmd_user_delete)
    return ap


def main():
    for stream in (sys.stdout, sys.stderr):   # 윈도우 콘솔에서 한글 오류 메시지가 깨지지 않게
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    load_dotenv()
    a = build_parser().parse_args()
    try:
        a.fn(Store(a.root), a)
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        sys.exit(f"오류: {e}")


if __name__ == "__main__":
    main()
