# Lesson design

Use the audited course pack rather than inventing a target list from memory.

## Inputs

- language: `es`, `fr`, `de`, `ja`, or `ko`
- scene: one of the six audited scenes, or an explicitly labeled on-demand topic from the bundled catalog
- duration: 5, 10, 20, or 40 minutes
- support mode: `immersion`（先独立表达、仅在需要时帮忙）, `guided`（默认；目标处给中文意图提示）, or `learning`（更早给提示与关键词/句型）。The mode changes support timing and amount, not the scene, A1 scope, or material volume.

Use `materials.py topics --format markdown` to show the learner the bundled topic catalog, `materials.py list` to resolve audited pack names, and `materials.py card` to obtain an audited subset. The six audited scenes are `cafe-order`, `directions-transit`, `doctor-visit`, `introductions`, `shopping`, and `making-plans`. If no exact pack exists, do not silently fall back to another language or scene.

For a topic marked `on_demand`, prepare a compact A1 exercise for the current session and label it `当次原创准备（非预置来源课程）`. Keep it separate from the audited curriculum: do not assign a material ID, source reference, or textbook-derived claim. If source-backed preparation is important to the learner, offer one of the six `audited_ready` scenes instead.

## Preparation card

Present, in this order:

1. language variety, scene, roles, and communication mission;
2. key words;
3. phrases or collocations;
4. complete sentence patterns;
5. register/politeness and one relevant culture or pronunciation note;
6. four story stages from the pack;
7. a measurable challenge.

Keep words, phrases, and sentence patterns visibly separate. A sentence pattern must remain a usable utterance, not a grammar label. Do not show a complete source dialogue.

## Scale by duration

The audited A1 packs are deliberately compact:

| Duration | Key words | Phrases | Sentence patterns | Challenge |
|---|---:|---:|---:|---|
| 5 min | 2 | 2 | 1 | independently use 2 selected targets |
| 10 min | 2 | 2 | 2 | independently use 3 selected targets |
| 20 min | 4 | 4 | 4 | complete all four story stages and use 5 targets |
| 40 min | 8 | 8 | 6 | complete all stages, handle one complication, and transfer 2 patterns |

The 20-minute card doubles the 10-minute keyword and phrase inventory; the 40-minute card doubles it again. Keep the added targets source-aware and scene-relevant, and do not inflate a longer card with near-duplicates. A 40-minute session still gains most of its depth through retesting, role changes, and a complication.

## Source behavior

The tool output includes provenance for internal use. Keep it out of the learner-facing card unless attribution or source inspection is requested. When requested, report source title, exact unit, usage role, and adaptation state. Never imply that `verification` material supplied the wording.
