# Workbench data

The multilingual workbench is a local, user-owned archive. It is separate from the English `kouyu` workbench and defaults to `multilingual-speaking-workbench` in the learner's home directory. If the learner requests another directory, use that same explicit path for both archive and serve operations.

## Session input

Write one JSON object after the report:

```json
{
  "id": "20260910-193000-fr-cafe-order",
  "created_at": "2026-09-10T19:30:00+08:00",
  "language": "fr",
  "scene": "cafe-order",
  "duration_minutes": 10,
  "level": "A1",
  "support_mode": "guided",
  "interaction_mode": "voice",
  "roles": {"learner": "customer", "coach": "barista"},
  "mission": "Order and modify a drink, then pay.",
  "mission_completed": true,
  "targets": [
    {
      "material_id": "fr.cafe.pattern.01",
      "status": "mastered",
      "support": "independent",
      "evidence": "Je voudrais un café, s'il vous plaît."
    }
  ],
  "repairs": [
    {
      "learner": "Je veux un café.",
      "natural": "Je voudrais un café, s'il vous plaît.",
      "reason_zh": "服务场景中条件式更柔和。"
    }
  ],
  "scores": {"task_completion": 4, "clarity": 4, "range": 3, "interaction": 4},
  "focus_next": ["fr.cafe.pattern.02"],
  "next_drill": "Order a different drink while keeping vous register.",
  "pronunciation": {
    "status": "observed",
    "evidence_mode": "live_audio",
    "notes": ["s’il vous plaît 的节奏组清楚；voudrais 的 /ʁ/ 仍可放松。"]
  }
}
```

Required target fields are `material_id`, `status`, and `support`. The archive command resolves all learning content and provenance from the bundled curriculum. This prevents a generated report from silently changing an expression or attributing it to the wrong source.

Allowed target statuses are `mastered`, `developing`, `needs_review`, and `not_observed`. Allowed support values are `independent`, `meaning_prompt`, `form_prompt`, `model`, and `none`.

`interaction_mode` is `text`, `voice`, or `mixed`. `observed` pronunciation is accepted only for a voice or mixed session with `evidence_mode` set to `live_audio` or `audio_file` and at least one concrete note. Text-only sessions and speech-to-text transcripts must use `not_observed` with `evidence_mode: none`.

Only audited Stage 2 material IDs can be archived. An ID from another language or scene is rejected. Prompted repetition is not `mastered` unless the learner later uses the target independently and correctly.

## Commands

```text
python <skill-directory>/scripts/workbench.py init
python <skill-directory>/scripts/workbench.py archive --input <session-json>
python <skill-directory>/scripts/workbench.py serve
```

To store the workbench elsewhere, pass the same explicit `--data-dir <workbench>` to every command.

`archive` is idempotent for an identical session. Reusing an ID with different content fails instead of overwriting history. `serve` opens the review-only UI; language, scene, duration, and support mode remain choices made in the conversation. The open page periodically reloads archive data so new records appear without restarting the server. Its default port is 8766.

## Adaptive review

The workbench derives recommendations at read time; it does not rewrite session history. For each `material_id`, only the chronologically latest observation determines whether the expression is due. `needs_review` ranks above `developing`, while stronger prompts and repeated unsuccessful observations increase priority. A later `mastered` observation removes the expression from the queue.

`GET /api/recommendations` returns the explainable review queue and one next-lesson choice. Without a `language` query, the next lesson follows the highest-priority due target across all five languages. An explicit `language` query constrains the choice to that language. If there is no due target in scope, it selects an unpracticed scene and then the least-practiced scene; empty history uses saved preferences. `limit` controls the returned queue size from 1 to 30.

This is evidence-based scheduling, not a claim about memory decay or pronunciation. It does not infer pronunciation from text, and it never changes a target's archived status.

## Reporting integrity

- Save only expressions that were part of the loaded preparation card.
- Distinguish independent use from meaning prompts, form prompts, and models.
- When pronunciation was not heard, store `pronunciation.status` as `not_observed` and `evidence_mode` as `none`.
- Do not place full source dialogues, copyrighted exercise instructions, or unverified original extensions in the archive.
