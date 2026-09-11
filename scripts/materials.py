#!/usr/bin/env python3
"""Resolve audited multilingual course packs into preparation-card data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CURRICULUM_ROOT = SKILL_ROOT / "curriculum"
LANGUAGE_ALIASES = {
    "es": "es", "spanish": "es", "西班牙语": "es", "西语": "es",
    "fr": "fr", "french": "fr", "法语": "fr",
    "de": "de", "german": "de", "德语": "de",
    "ja": "ja", "japanese": "ja", "日语": "ja",
    "ko": "ko", "korean": "ko", "韩语": "ko",
}
SCENE_ALIASES = {
    "cafe-order": "cafe-order", "cafe": "cafe-order", "coffee": "cafe-order",
    "咖啡店": "cafe-order", "点单": "cafe-order",
    "directions-transit": "directions-transit", "directions": "directions-transit",
    "transit": "directions-transit", "问路": "directions-transit", "交通": "directions-transit",
    "doctor-visit": "doctor-visit", "doctor": "doctor-visit", "medical": "doctor-visit",
    "看医生": "doctor-visit", "就医": "doctor-visit",
    "introductions": "introductions", "introduction": "introductions", "meet": "introductions",
    "自我介绍": "introductions", "认识": "introductions",
    "shopping": "shopping", "shop": "shopping", "购物": "shopping", "买东西": "shopping",
    "making-plans": "making-plans", "plans": "making-plans", "invitation": "making-plans",
    "约计划": "making-plans", "邀请": "making-plans", "约时间": "making-plans",
}
LANGUAGE_LABELS = {"es": "西班牙语", "fr": "法语", "de": "德语", "ja": "日语", "ko": "韩语"}


def curriculum_root() -> Path:
    return DEFAULT_CURRICULUM_ROOT


def load_json(path: Path):
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def load_data() -> tuple[dict, dict, list[dict]]:
    root = curriculum_root()
    required = ["sample-packs.json", "scene-map.json", "sources.json"]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(f"curriculum data missing from {root}: {', '.join(missing)}")
    return (
        load_json(root / "sample-packs.json"),
        load_json(root / "scene-map.json"),
        load_json(root / "sources.json"),
    )


def load_target_extensions() -> dict:
    path = curriculum_root() / "target-extensions.json"
    if not path.is_file():
        raise FileNotFoundError(f"target extensions missing from {curriculum_root()}: {path.name}")
    return load_json(path)


def load_topic_catalog() -> dict:
    path = curriculum_root() / "topic-catalog.json"
    if not path.is_file():
        raise FileNotFoundError(f"topic catalog missing from {curriculum_root()}: {path.name}")
    return load_json(path)


def normalize(value: str, aliases: dict[str, str], label: str) -> str:
    key = value.strip().lower()
    if key not in aliases:
        allowed = ", ".join(sorted(set(aliases.values())))
        raise ValueError(f"unsupported {label} {value!r}; choose one of: {allowed}")
    return aliases[key]


def target_counts(duration: int) -> tuple[int, int, int, int]:
    if not 1 <= duration <= 60:
        raise ValueError("duration must be between 1 and 60 minutes")
    if duration <= 5:
        return 2, 2, 1, 2
    if duration <= 10:
        return 2, 2, 2, 3
    if duration <= 20:
        return 4, 4, 4, 5
    return 8, 8, 6, 7


def preview_counts(duration: int) -> tuple[int, int, int]:
    """Return learner-facing preparation-card minimums.

    The audited pack remains a compact active-practice core. The skill fills the
    difference with clearly non-audited, session-original recognition material.
    """
    if not 1 <= duration <= 60:
        raise ValueError("duration must be between 1 and 60 minutes")
    if duration <= 5:
        return 15, 3, 2
    if duration <= 10:
        return 20, 5, 3
    if duration <= 20:
        return 30, 8, 5
    return 40, 12, 8


def expanded_targets(pack: dict, language: str, scene: str, field: str) -> list[dict]:
    """Append source-aware long-session targets while preserving the compact base pack."""
    base = list(pack.get(field, []))
    extension_key = f"{language}.{scene}"
    extension = load_target_extensions().get("packs", {}).get(extension_key, {}).get(field, [])
    singular = "keyword" if field == "keywords" else "phrase"
    # Verification references document checks only; they must not be presented as
    # the wording source for newly adapted targets.
    source_refs = [ref for ref in pack.get("source_refs", []) if ref.get("role") == "basis"]
    for index, item in enumerate(extension, start=len(base) + 1):
        enriched = {
            "id": f"{pack['id']}.{singular}.{index:02d}",
            **item,
            "source_refs": source_refs,
            "adaptation": "original_rewrite",
        }
        base.append(enriched)
    return base


def build_card(language: str, scene: str, level: str, duration: int) -> dict:
    sample_data, scene_data, source_data = load_data()
    language = normalize(language, LANGUAGE_ALIASES, "language")
    scene = normalize(scene, SCENE_ALIASES, "scene")
    level = level.upper()
    pack = next(
        (
            item for item in sample_data.get("packs", [])
            if item.get("language") == language and item.get("scene") == scene and item.get("level", "").upper() == level
        ),
        None,
    )
    if pack is None:
        raise ValueError(f"no audited A1 pack for {language}/{scene}/{level}")

    scene_entry = next(item for item in scene_data.get("scenes", []) if item.get("id") == scene)
    mappings = scene_entry.get("mappings", {}).get(language, [])
    source_index = {source["id"]: source for source in source_data}
    keyword_count, phrase_count, pattern_count, challenge_count = target_counts(duration)
    preview_keyword_count, preview_phrase_count, preview_pattern_count = preview_counts(duration)
    refs = []
    for ref in pack.get("source_refs", []):
        source = source_index[ref["source_id"]]
        refs.append({
            **ref,
            "title": source["title"],
            "license": source["license"],
            "usage": source["usage"],
            "url": source["url"],
        })

    return {
        "schema_version": 1,
        "pack_id": pack["id"],
        "language": language,
        "language_label_zh": LANGUAGE_LABELS[language],
        "scene": scene,
        "scene_label_zh": scene_entry.get("label_zh", scene),
        "level": level,
        "duration_minutes": duration,
        "language_policy": sample_data["languages"][language],
        "communication_tasks": scene_entry.get("communication_tasks", []),
        "keywords": expanded_targets(pack, language, scene, "keywords")[:keyword_count],
        "phrases": expanded_targets(pack, language, scene, "phrases")[:phrase_count],
        "sentence_patterns": pack.get("sentence_patterns", [])[:pattern_count],
        "preview_plan": {
            "keyword_count": preview_keyword_count,
            "phrase_count": preview_phrase_count,
            "sentence_pattern_count": preview_pattern_count,
            "audited_core_counts": {
                "keywords": keyword_count,
                "phrases": phrase_count,
                "sentence_patterns": pattern_count,
            },
            "supplement_required": True,
            "supplement_policy": "Fill any gap with A1-appropriate session-original recognition material; do not assign it audited IDs or provenance.",
        },
        "politeness_note_zh": pack.get("politeness_note_zh", ""),
        "register_pairs": pack.get("register_pairs", []),
        "pronunciation_focus": pack.get("pronunciation_focus", []),
        "story_nodes": pack.get("story_nodes", []),
        "challenge": {
            "independent_target_count": challenge_count,
            "complete_all_story_nodes": duration > 10,
            "include_complication": duration > 20,
        },
        "source_refs": refs,
        "source_mappings": mappings,
        "source_boundary": "partial" if any(item.get("status") == "partial_verified" for item in mappings) else "verified",
        "adaptation": pack.get("adaptation"),
    }


def display_item(item: dict, show_romanization: bool) -> str:
    text = f"- {item['surface']} — {item['meaning_zh']}"
    reading = item.get("reading")
    if reading and reading != item["surface"]:
        text += f"（读音：{reading}）"
    if show_romanization and item.get("romanization"):
        text += f" [{item['romanization']}]"
    return text


def render_markdown(card: dict, show_romanization: bool) -> str:
    lines = [
        f"# {card['language_label_zh']} · {card['scene_label_zh']}",
        "",
        f"- 级别：{card['level']}",
        f"- 时长：{card['duration_minutes']} 分钟",
        f"- 语言标准：{card['language_policy']['standard']}",
        f"- 最终预习卡数量：{card['preview_plan']['keyword_count']} 个关键词、{card['preview_plan']['phrase_count']} 个词组、{card['preview_plan']['sentence_pattern_count']} 个完整句型",
        "- 以下是已审定核心；Skill 会用无虚假来源标注的当次原创内容补足最终预习卡。",
        "",
        "## 关键词",
        "",
    ]
    lines.extend(display_item(item, show_romanization) for item in card["keywords"])
    lines += ["", "## 词组", ""]
    lines.extend(display_item(item, show_romanization) for item in card["phrases"])
    lines += ["", "## 完整句型", ""]
    lines.extend(display_item(item, show_romanization) for item in card["sentence_patterns"])
    if card["register_pairs"]:
        lines += ["", "## 称呼与礼貌", ""]
        for pair in card["register_pairs"]:
            lines += [
                f"- 熟悉关系：{pair['informal']}",
                f"- 正式或陌生关系：{pair['formal']}",
                f"- {pair['note_zh']}",
            ]
    if card["pronunciation_focus"]:
        lines += ["", "## 发音关注", ""]
        lines.extend(f"- {item}" for item in card["pronunciation_focus"])
    lines += [
        "",
        "## 场景推进",
        "",
        " → ".join(card["story_nodes"]),
        "",
        f"挑战：独立使用至少 {card['challenge']['independent_target_count']} 个目标表达。",
    ]
    if card["politeness_note_zh"]:
        lines.insert(-1, f"礼貌与场合：{card['politeness_note_zh']}")
    return "\n".join(lines) + "\n"


def list_packs() -> dict:
    sample_data, scene_data, _ = load_data()
    return {
        "languages": sample_data.get("languages", {}),
        "scenes": [
            {"id": scene["id"], "label_zh": scene.get("label_zh", scene["id"])}
            for scene in scene_data.get("scenes", [])
        ],
        "packs": [
            {
                "id": pack["id"],
                "language": pack["language"],
                "scene": pack["scene"],
                "level": pack["level"],
            }
            for pack in sample_data.get("packs", [])
        ],
    }


def list_topics(language: str | None = None) -> dict:
    catalog = load_topic_catalog()
    if language is not None:
        language = normalize(language, LANGUAGE_ALIASES, "language")
    topics = []
    for topic in catalog.get("topics", []):
        status = topic["status"]
        status_info = catalog["statuses"][status]
        topics.append({
            **topic,
            "status_label_zh": status_info["label_zh"],
            "status_description_zh": status_info["description_zh"],
        })
    return {
        "schema_version": catalog.get("schema_version", 1),
        "language": language,
        "language_label_zh": LANGUAGE_LABELS.get(language) if language else None,
        "languages": catalog.get("languages", []),
        "topics": topics,
    }


def render_topic_table(catalog: dict) -> str:
    heading = "可选口语主题"
    if catalog.get("language_label_zh"):
        heading = f"{catalog['language_label_zh']}可选口语主题"
    lines = [
        f"## {heading}",
        "",
        "| # | 主题 | 准备状态 | 使用说明 |",
        "|---:|---|---|---|",
    ]
    for index, topic in enumerate(catalog["topics"], start=1):
        if topic["status"] == "audited_ready":
            note = "Skill 内置有来源 A1 预习资料，可直接开始"
        else:
            note = "当次原创准备，无预置来源课程"
        lines.append(f"| {index} | {topic['label_zh']} | {topic['status_label_zh']} | {note} |")
    return "\n".join(lines) + "\n"


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list audited A1 packs")
    topics = commands.add_parser("topics", help="list prepared and on-demand speaking topics")
    topics.add_argument("--language")
    topics.add_argument("--format", choices=("json", "markdown"), default="json")
    card = commands.add_parser("card", help="build a preparation-card payload")
    card.add_argument("--language", required=True)
    card.add_argument("--scene", required=True)
    card.add_argument("--level", default="A1")
    card.add_argument("--duration", type=int, default=10)
    card.add_argument("--format", choices=("json", "markdown"), default="json")
    card.add_argument("--romanization", action="store_true", help="include optional romanization in Markdown")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "list":
            payload = list_packs()
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.command == "topics":
            payload = list_topics(args.language)
            if args.format == "markdown":
                print(render_topic_table(payload), end="")
            else:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        card = build_card(args.language, args.scene, args.level, args.duration)
        if args.format == "markdown":
            print(render_markdown(card, args.romanization), end="")
        else:
            print(json.dumps(card, ensure_ascii=False, indent=2))
        return 0
    except (FileNotFoundError, KeyError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
