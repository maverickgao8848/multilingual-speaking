#!/usr/bin/env python3
"""Archive multilingual speaking sessions and serve the local review workbench."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
import threading
import webbrowser
from collections import defaultdict
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import materials


VERSION = 2
MAX_BODY = 2 * 1024 * 1024
LANGUAGES = {"es", "fr", "de", "ja", "ko"}
ALLOWED_STATUS = {"mastered", "developing", "needs_review", "not_observed"}
ALLOWED_SUPPORT = {"independent", "meaning_prompt", "form_prompt", "model", "none"}
ALLOWED_INTERACTION = {"text", "voice", "mixed"}
ALLOWED_PRONUNCIATION = {"not_observed", "observed"}
LANGUAGE_LABELS = {"es": "西班牙语", "fr": "法语", "de": "德语", "ja": "日语", "ko": "韩语"}
LANGUAGE_EMOJI = {"es": "🇲🇽", "fr": "🇫🇷", "de": "🇩🇪", "ja": "🇯🇵", "ko": "🇰🇷"}
SCENE_EMOJI = {"cafe-order": "☕", "directions-transit": "🚇", "doctor-visit": "🩺", "introductions": "👋", "shopping": "🛍", "making-plans": "📅"}
STATUS_PRIORITY = {"needs_review": 100, "developing": 70, "not_observed": 40}
SUPPORT_PRIORITY = {"model": 25, "form_prompt": 18, "meaning_prompt": 10, "none": 4, "independent": 0}
STATUS_LABELS = {"needs_review": "需要重练", "developing": "正在形成", "not_observed": "尚未观察"}
SUPPORT_LABELS = {"model": "依赖示范", "form_prompt": "需要形式提示", "meaning_prompt": "需要意义提示", "none": "尚无独立证据", "independent": "可独立使用"}


def scene_metadata() -> dict[str, dict]:
    return {scene["id"]: scene for scene in materials.list_packs()["scenes"]}


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def empty_state() -> dict:
    return {
        "version": VERSION,
        "preferences": {"language": "es", "scene": "cafe-order", "duration": 10, "support_mode": "guided", "interaction_mode": "text"},
        "sessions": [],
    }


def require(value: object, expected: type, label: str) -> None:
    if not isinstance(value, expected):
        raise ValueError(f"{label} must be {expected.__name__}")


def material_index() -> dict[str, dict]:
    sample_data, _, _ = materials.load_data()
    index: dict[str, dict] = {}
    for pack in sample_data.get("packs", []):
        for group in ("keywords", "phrases", "sentence_patterns"):
            for item in pack.get(group, []):
                index[item["id"]] = {
                    **item,
                    "language": pack["language"],
                    "scene": pack["scene"],
                    "level": pack["level"],
                    "material_type": group,
                }
    return index


def validate_preferences(preferences: dict) -> None:
    require(preferences, dict, "preferences")
    if preferences.get("language") not in LANGUAGES:
        raise ValueError("preferences.language is invalid")
    if preferences.get("scene") not in scene_metadata():
        raise ValueError("preferences.scene is invalid")
    if preferences.get("duration") not in {5, 10, 20, 40}:
        raise ValueError("preferences.duration is invalid")
    if preferences.get("support_mode") not in {"immersion", "guided", "learning"}:
        raise ValueError("preferences.support_mode is invalid")
    if preferences.get("interaction_mode", "text") not in ALLOWED_INTERACTION:
        raise ValueError("preferences.interaction_mode is invalid")


def validate_session(session: dict, index: dict[str, dict] | None = None) -> None:
    require(session, dict, "session")
    for field in ("id", "created_at", "language", "scene", "duration_minutes", "level", "support_mode", "targets"):
        if field not in session:
            raise ValueError(f"missing required field: {field}")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", str(session["id"])):
        raise ValueError("id may contain only letters, digits, dot, underscore, and hyphen")
    if session["language"] not in LANGUAGES:
        raise ValueError("language is invalid")
    if session["scene"] not in scene_metadata():
        raise ValueError("scene is invalid")
    if session["level"].upper() != "A1":
        raise ValueError("Stage 2 archives only audited A1 sessions")
    if session["support_mode"] not in {"immersion", "guided", "learning"}:
        raise ValueError("support_mode is invalid")
    interaction_mode = session.get("interaction_mode", "text")
    if interaction_mode not in ALLOWED_INTERACTION:
        raise ValueError("interaction_mode is invalid")
    if not isinstance(session["duration_minutes"], (int, float)) or not 1 <= session["duration_minutes"] <= 60:
        raise ValueError("duration_minutes must be between 1 and 60")
    require(session["targets"], list, "targets")
    if index is None:
        index = material_index()
    for position, target in enumerate(session["targets"]):
        require(target, dict, f"targets[{position}]")
        material_id = target.get("material_id")
        if material_id not in index:
            raise ValueError(f"targets[{position}].material_id is not in the audited curriculum")
        canonical = index[material_id]
        if canonical["language"] != session["language"] or canonical["scene"] != session["scene"]:
            raise ValueError(f"targets[{position}] does not belong to this language and scene")
        if target.get("status") not in ALLOWED_STATUS:
            raise ValueError(f"targets[{position}].status is invalid")
        if target.get("support", "none") not in ALLOWED_SUPPORT:
            raise ValueError(f"targets[{position}].support is invalid")
    pronunciation = session.get("pronunciation", {"status": "not_observed", "notes": []})
    require(pronunciation, dict, "pronunciation")
    if pronunciation.get("status") not in ALLOWED_PRONUNCIATION:
        raise ValueError("pronunciation.status is invalid")
    require(pronunciation.get("notes", []), list, "pronunciation.notes")
    evidence_mode = pronunciation.get("evidence_mode", "none")
    if pronunciation["status"] == "observed":
        if interaction_mode == "text" or evidence_mode not in {"live_audio", "audio_file"}:
            raise ValueError("observed pronunciation requires heard audio evidence")
        if not pronunciation.get("notes") or not all(isinstance(note, str) and note.strip() for note in pronunciation["notes"]):
            raise ValueError("observed pronunciation requires non-empty notes")
    elif evidence_mode != "none":
        raise ValueError("not_observed pronunciation must use evidence_mode none")


def canonical_session(session: dict) -> dict:
    index = material_index()
    validate_session(session, index)
    normalized = json.loads(json.dumps(session, ensure_ascii=False))
    normalized["level"] = "A1"
    normalized.setdefault("interaction_mode", "text")
    normalized.setdefault("pronunciation", {"status": "not_observed", "notes": []})
    normalized["pronunciation"].setdefault("evidence_mode", "none")
    for target in normalized["targets"]:
        canonical = index[target["material_id"]]
        for field in ("surface", "meaning_zh", "reading", "romanization", "source_refs", "adaptation", "material_type"):
            if field in canonical:
                target[field] = canonical[field]
        target.setdefault("support", "none")
        target.setdefault("evidence", "")
    normalized["provenance"] = "audited_curriculum"
    return normalized


def validate_state(state: dict) -> None:
    require(state, dict, "state")
    validate_preferences(state.get("preferences", {}))
    require(state.get("sessions"), list, "sessions")
    index = material_index()
    for session in state["sessions"]:
        validate_session(session, index)


def load_state(data_dir: Path) -> dict:
    path = data_dir / "workbench-data.json"
    if not path.exists():
        state = empty_state()
        atomic_json(path, state)
        return state
    with path.open(encoding="utf-8-sig") as handle:
        state = json.load(handle)
    state.setdefault("preferences", {}).setdefault("interaction_mode", "text")
    validate_state(state)
    return state


def render_dashboard(state: dict) -> str:
    sessions = sorted(state["sessions"], key=lambda item: item.get("created_at", ""), reverse=True)
    lines = ["# 多语种口语复习台", "", f"> 已归档 {len(sessions)} 次练习。", ""]
    if not sessions:
        lines += ["还没有练习记录。完成第一次五语场景练习后，这里会生成复习内容。", ""]
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for session in sessions:
        grouped[(session["language"], session["scene"])].append(session)
    scenes = scene_metadata()
    for (language, scene), items in grouped.items():
        targets = [target for item in items for target in item.get("targets", [])]
        mastered = sum(target.get("status") == "mastered" for target in targets)
        review = list(dict.fromkeys(
            target.get("surface", "") for target in targets if target.get("status") == "needs_review"
        ))[:6]
        lines += [f"## {LANGUAGE_EMOJI[language]} {LANGUAGE_LABELS[language]} · {SCENE_EMOJI.get(scene, '·')} {scenes[scene].get('label_zh', scene)}", ""]
        lines += [
            f"- 练习次数：{len(items)}",
            f"- 已掌握：{mastered}/{len(targets)}",
            f"- 最近练习：{items[0].get('created_at', '')}",
        ]
        if review:
            lines.append(f"- 下次复习：{'、'.join(filter(None, review))}")
        lines.append("")
    lines += ["---", "", f"更新时间：{datetime.now().astimezone().isoformat(timespec='seconds')}", ""]
    return "\n".join(lines)


def save_state(data_dir: Path, state: dict) -> None:
    validate_state(state)
    state["version"] = VERSION
    atomic_json(data_dir / "workbench-data.json", state)
    (data_dir / "复习台.md").write_text(render_dashboard(state), encoding="utf-8")


def init_workbench(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    save_state(data_dir, load_state(data_dir))
    print(f"Multilingual workbench ready: {data_dir.resolve()}")


def archive_session(data_dir: Path, input_path: Path) -> None:
    with input_path.open(encoding="utf-8-sig") as handle:
        session = canonical_session(json.load(handle))
    state = load_state(data_dir)
    existing = next((item for item in state["sessions"] if item["id"] == session["id"]), None)
    if existing is not None and existing != session:
        raise ValueError(f"session id already exists with different data: {session['id']}")
    if existing is None:
        state["sessions"].append(session)
    sessions_dir = data_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(sessions_dir / f"{session['id']}.json", session)
    save_state(data_dir, state)
    print(f"Archived: {session['id']}")


def catalog_payload() -> dict:
    listed = materials.list_packs()
    return {
        "languages": [
            {"id": code, "label": LANGUAGE_LABELS[code], "emoji": LANGUAGE_EMOJI[code], **listed["languages"][code]}
            for code in sorted(LANGUAGES)
        ],
        "scenes": [
            {"id": scene["id"], "label": scene["label_zh"], "emoji": SCENE_EMOJI.get(scene["id"], "💬")}
            for scene in listed["scenes"]
        ],
    }


def recommendation_payload(state: dict, language: str | None = None, limit: int = 8) -> dict:
    """Build a deterministic, explainable review queue from archived evidence."""
    validate_state(state)
    requested_language = language
    if requested_language is not None and requested_language not in LANGUAGES:
        raise ValueError("recommendation language is invalid")
    if not isinstance(limit, int) or not 1 <= limit <= 30:
        raise ValueError("recommendation limit must be between 1 and 30")

    index = material_index()
    sessions = sorted(state["sessions"], key=lambda item: (item.get("created_at", ""), item["id"]))
    latest: dict[str, dict] = {}
    attempts: defaultdict[str, int] = defaultdict(int)
    pack_counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    for session in sessions:
        pack_counts[(session["language"], session["scene"])] += 1
        for target in session.get("targets", []):
            material_id = target["material_id"]
            attempts[material_id] += 1
            latest[material_id] = {
                **target,
                "language": session["language"],
                "scene": session["scene"],
                "last_seen": session["created_at"],
                "session_id": session["id"],
            }

    queue = []
    for material_id, observation in latest.items():
        status = observation["status"]
        if status == "mastered":
            continue
        score = STATUS_PRIORITY[status] + SUPPORT_PRIORITY[observation.get("support", "none")]
        score += min(max(attempts[material_id] - 1, 0) * 4, 12)
        canonical = index[material_id]
        reasons = [STATUS_LABELS[status]]
        support = observation.get("support", "none")
        if support != "independent":
            reasons.append(SUPPORT_LABELS[support])
        if attempts[material_id] > 1:
            reasons.append(f"已出现 {attempts[material_id]} 次")
        queue.append({
            "material_id": material_id,
            "surface": canonical["surface"],
            "meaning_zh": canonical["meaning_zh"],
            "reading": canonical.get("reading"),
            "romanization": canonical.get("romanization"),
            "material_type": canonical["material_type"],
            "language": observation["language"],
            "scene": observation["scene"],
            "status": status,
            "support": support,
            "last_seen": observation["last_seen"],
            "attempts": attempts[material_id],
            "priority": score,
            "reasons": reasons,
        })
    queue.sort(key=lambda item: (-item["priority"], item["last_seen"], item["material_id"]))

    if requested_language is None:
        language = queue[0]["language"] if queue else state["preferences"]["language"]
    else:
        language = requested_language
    language_due = [item for item in queue if item["language"] == language]
    scenes = list(scene_metadata())
    preferences = state["preferences"]
    if language_due:
        chosen_scene = language_due[0]["scene"]
        chosen_targets = [item for item in language_due if item["scene"] == chosen_scene][:4]
        reason = f"优先回练 {chosen_targets[0]['surface']}：{'，'.join(chosen_targets[0]['reasons'])}。"
        recommendation_type = "review"
    else:
        unpracticed = [scene for scene in scenes if pack_counts[(language, scene)] == 0]
        if unpracticed:
            chosen_scene = preferences["scene"] if preferences["scene"] in unpracticed else unpracticed[0]
            reason = "这个场景还没有练习记录，适合补齐 A1 生活任务覆盖。"
            recommendation_type = "new_scene"
        else:
            chosen_scene = min(scenes, key=lambda scene: (pack_counts[(language, scene)], scenes.index(scene)))
            reason = "当前没有待复习表达，建议巩固练习次数最少的场景。"
            recommendation_type = "maintenance"
        chosen_targets = []

    scene = scene_metadata()[chosen_scene]
    return {
        "version": VERSION,
        "basis": "latest_observation",
        "language": language,
        "review_queue": queue[:limit],
        "overview": {
            "unique_targets_observed": len(latest),
            "targets_due": len(queue),
            "language_targets_due": len(language_due),
        },
        "next_lesson": {
            "type": recommendation_type,
            "language": language,
            "scene": chosen_scene,
            "scene_label": scene.get("label_zh", chosen_scene),
            "pack_id": f"{language}.{chosen_scene}.a1",
            "duration": preferences["duration"],
            "support_mode": preferences["support_mode"],
            "interaction_mode": preferences.get("interaction_mode", "text"),
            "review_target_ids": [item["material_id"] for item in chosen_targets],
            "reason": reason,
        },
    }


def make_handler(data_dir: Path, static_dir: Path):
    class WorkbenchHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(static_dir), **kwargs)

        def send_json(self, payload: object, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/health":
                    self.send_json({"ok": True, "version": VERSION})
                    return
                if parsed.path == "/api/state":
                    self.send_json(load_state(data_dir))
                    return
                if parsed.path == "/api/catalog":
                    self.send_json(catalog_payload())
                    return
                if parsed.path == "/api/recommendations":
                    query = parse_qs(parsed.query)
                    selected_language = query.get("language", [None])[0]
                    limit = int(query.get("limit", ["8"])[0])
                    self.send_json(recommendation_payload(load_state(data_dir), selected_language, limit))
                    return
                if parsed.path == "/api/card":
                    query = parse_qs(parsed.query)
                    card = materials.build_card(
                        query.get("language", [""])[0],
                        query.get("scene", [""])[0],
                        "A1",
                        int(query.get("duration", ["10"])[0]),
                    )
                    self.send_json(card)
                    return
                super().do_GET()
            except (FileNotFoundError, KeyError, TypeError, ValueError) as error:
                self.send_json({"error": str(error)}, 400)

        def do_PUT(self):
            if urlparse(self.path).path != "/api/preferences":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    raise ValueError("invalid request size")
                preferences = json.loads(self.rfile.read(length).decode("utf-8"))
                validate_preferences(preferences)
                state = load_state(data_dir)
                state["preferences"] = preferences
                save_state(data_dir, state)
                self.send_json({"ok": True})
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error)}, 400)

        def log_message(self, format_string, *args):
            print(f"[{self.log_date_time_string()}] {format_string % args}")

    return WorkbenchHandler


def serve(data_dir: Path, host: str, port: int, open_browser: bool) -> None:
    init_workbench(data_dir)
    static_dir = Path(__file__).resolve().parent.parent / "assets" / "workbench"
    if not (static_dir / "index.html").is_file():
        raise FileNotFoundError(f"workbench UI missing: {static_dir}")
    server = ThreadingHTTPServer((host, port), make_handler(data_dir, static_dir))
    actual_port = server.server_address[1]
    url = f"http://{host}:{actual_port}/"
    print(f"Listening on {url}")
    if open_browser:
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "archive"):
        sub = commands.add_parser(command)
        sub.add_argument("--data-dir", type=Path, default=Path.cwd() / "multilingual-speaking-workbench")
        if command == "archive":
            sub.add_argument("--input", type=Path, required=True)
    sub = commands.add_parser("serve")
    sub.add_argument("--data-dir", type=Path, default=Path.cwd() / "multilingual-speaking-workbench")
    sub.add_argument("--host", default="127.0.0.1")
    sub.add_argument("--port", type=int, default=8766)
    sub.add_argument("--no-open", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            init_workbench(args.data_dir)
        elif args.command == "archive":
            archive_session(args.data_dir, args.input)
        else:
            serve(args.data_dir, args.host, args.port, not args.no_open)
        return 0
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
