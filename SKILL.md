---
name: multilingual-speaking
description: Run A1 text or voice speaking practice in Spanish, French, German, Japanese, or Korean with Chinese guidance, a proactive 26-topic menu, source-aware preparation cards for six audited scenes, clearly labeled on-demand preparation for 20 additional practical scenes, role-play, correction, and review. Use whenever a learner wants guided speaking practice or asks what scenarios are available in any of these five languages.
compatibility: Self-contained skill. Python 3.10+ is needed for bundled curriculum lookup and local workbench persistence; no external course-data directory or service is required.
---

# Multilingual Speaking

Turn an audited course pack into a short speaking loop: choose, preview, role-play, repair, and review. This skill is separate from `kouyu`; send English practice to that skill.

## Route the request

- For language defaults, scripts, register, and romanization policy, read [references/language-policy.md](references/language-policy.md).
- Before building a preparation card, read [references/lesson-design.md](references/lesson-design.md).
- Before starting or continuing role-play, read [references/session-protocol.md](references/session-protocol.md).
- When saving or reviewing progress, read [references/workbench-data.md](references/workbench-data.md).
- Resolve learning material through `python <skill-directory>/scripts/materials.py`; at runtime it reads only the curriculum bundled inside this skill folder. Do not silently substitute remembered textbook content or an external course-data directory.
- Resolve the visible topic menu through the same script; its catalog is also bundled inside the skill folder.

## Supported A1 scope

- Languages: Spanish (`es`), French (`fr`), German (`de`), Japanese (`ja`), Korean (`ko`).
- Audited level: A1.
- Audited, ready scenes: café ordering, directions/public transport, a doctor visit, introductions, shopping, and making plans.
- On-demand catalog: 20 additional practical topics for each supported language. These are session-original exercises, not pre-sourced curriculum.
- Durations: 5, 10, 20, or 40 minutes. The duration changes how much of the pack is previewed and rehearsed, not the claimed CEFR level. The 20-minute card uses 4 keywords and 4 phrases; the 40-minute card uses 8 of each.

If the learner asks for an unsupported language or higher level, say that the audited A1 curriculum does not cover it. For a catalog topic marked `on_demand`, offer an explicitly labeled original, non-curriculum exercise. Never present an original extension as textbook-derived.

## Start a session

Collect only missing choices: target language, scene, approximate duration, support mode, and interaction channel when it matters. Default to 10 minutes, `guided`, and the current channel. When asking the learner to choose a support mode, explain the options clearly:

- `immersion`（沉浸式）：尽量完全用目标语言推进，先不附中文提示、关键词或句型；只有卡住、听不懂或明确求助时才逐级提供帮助。适合模拟真实出行或社交场景、检验独立表达的人。
- `guided`（引导式，默认）：以目标语言对话为主；需要带出练习目标时，会给简短中文提示，说明“要表达什么”，但不直接给答案。适合希望保持对话感、又不想频繁卡住的大多数学习者。
- `learning`（学习式）：更早给中文意图提示，并可较快给出目标语言关键词或未完成句型；完整范句仍只在需要或请求时提供。适合刚学该语言、刚接触该场景，或希望边说边积累表达的人。

All three modes use the same scene, A1 scope, and review standard. They differ only in when and how much support is offered during the conversation. Interaction modes are `text`, `voice`, and `mixed`.

When the learner has not selected a scene, proactively run:

```text
python <skill-directory>/scripts/materials.py topics --language <code> --format markdown
```

Omit `--language` when the language is also unknown. Show the returned table before asking the learner to choose. Keep the two preparation states visible: `已备课` means the source-backed pack is ready; `需现场准备` means an original exercise will be created for this session. Do not collapse or rename the states in a way that obscures this distinction.

Treat the visible menu as a prerequisite for any numbered scene question, not as optional background. A range such as “1–26”, a couple of recommendations, or examples such as “1（咖啡店）/ 4（自我介绍）” does not let the learner see the available choices.

Before sending a turn that asks for a scene number, verify all of the following:

1. That same assistant turn contains the complete Markdown topic table returned by `materials.py` for the selected language.
2. All 26 numbered rows and both preparation-state columns are visible; do not summarize, hide, truncate, or defer the table to a later turn.
3. The question appears after the table and asks for either a number or a topic name.

If any check fails, do not ask “请选择几号” yet. Run the command, print its output verbatim, and then ask. If the learner changes the language before choosing a scene, display the new language's complete table again. If the learner already names a scene in words, resolve it directly and do not force a numbered choice.

Example for a partially specified request such as `日语，一分钟，guided`:

```text
[first show the complete output of: materials.py topics --language ja --format markdown]

请从上表回复主题编号或主题名称；例如“1”或“咖啡店点单”。
```

Do not respond only with `请选择主题编号 1–26` or with a short list of suggested numbers.

For an `audited_ready` topic, load the matching card data:

```text
python <skill-directory>/scripts/materials.py card --language <code> --scene <scene-id> --duration <minutes>
```

Present a compact preparation card containing the situation, roles, mission, key words, phrases, complete sentence patterns, register or politeness note, story stages, and a measurable challenge. For Japanese and Korean, follow the display rules in the language policy. Do not show a complete dialogue.

For an `on_demand` topic, use the same compact card shape but put `资料状态：当次原创准备（非预置来源课程）` near the top. Do not invent provenance, material IDs, or claims of prior auditing, and do not archive invented targets as audited curriculum items.

End the card with two controls in the target language plus Chinese explanation: a natural readiness signal to begin and a clear signal to stop and review. Treat equivalent wording as the same intent.

## Run the role-play

State both roles and the mission briefly, then stay in character. Use the target language for the scene and Chinese only for concise learning support. Keep one speakable question per turn.

Track each selected target internally as modeled, meaning-prompted, form-prompted, independently used, correctly used, or needing retest. Create natural opportunities for uncovered targets; do not turn the exchange into recitation.

Respect the relationship encoded by the pack. Do not switch casually between `tú/usted`, `tu/vous`, `du/Sie`, or Korean speech levels. In Japanese and Korean, accept natural subject omission. Correct only errors that block meaning, recur, or concern a selected target, then return immediately to the scene.

## Finish

When the learner clearly asks to stop, leave character immediately. Report:

1. whether the communication mission was completed;
2. independently used, prompted, and not-yet-used targets;
3. two or three high-value corrections with natural replacements;
4. one register, culture, or pronunciation note that is supported by the interaction;
5. one short transfer drill for next time.

Never infer pronunciation from typed text or speech-to-text output. Only record an observed pronunciation note when actual audio was available under the evidence rules in the session protocol. Preserve acceptable regional forms and explain the variant instead of “correcting” them into the default standard.

When local file access is available, archive the structured result unless the learner opts out. Resolve the script relative to this skill and run:

```text
python <skill-directory>/scripts/workbench.py archive --input <session.json> --data-dir <workbench-directory>
```

Default to `multilingual-speaking-workbench` in the active workspace. The archive tool restores each target's exact surface form, meaning, reading, romanization, adaptation, and source references from its `material_id`; do not hand-copy those provenance fields.

When the learner asks what to practice next, use the workbench recommendation rather than guessing from the curriculum order. With the local server running, read `/api/recommendations`; otherwise use the rules in [references/workbench-data.md](references/workbench-data.md). Explain the selected scene and review targets briefly. Treat the queue as a recommendation derived from recorded evidence, not as a proficiency diagnosis.

## Source integrity

Treat the loaded pack as the material boundary. `basis` references may ground adaptations; `verification` references only document checks. A `partial_verified` scene mapping supports only its declared `coverage`. Do not reconstruct or quote full textbook dialogues, and do not expose internal source metadata unless the learner asks where an expression came from.
