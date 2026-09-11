# Lesson design

Use the audited course pack as the active-practice core. Build a broader learner-facing recognition vocabulary bank around that core so the learner can understand the real options in the scene.

## Inputs

- language: `es`, `fr`, `de`, `ja`, or `ko`
- scene: one of the six audited scenes, or an explicitly labeled on-demand topic from the bundled catalog
- duration: 5, 10, 20, or 40 minutes
- support mode: `immersion`（先独立表达、仅在需要时帮忙）, `guided`（默认；目标处给中文意图提示）, or `learning`（更早给提示与关键词/句型）。The mode changes support timing and amount, not the scene, A1 scope, or material volume.

Use `materials.py topics --format markdown` to show the learner the bundled topic catalog, `materials.py list` to resolve audited pack names, and `materials.py card` to obtain an audited subset. The six audited scenes are `cafe-order`, `directions-transit`, `doctor-visit`, `introductions`, `shopping`, and `making-plans`. If no exact pack exists, do not silently fall back to another language or scene.

For a topic marked `on_demand`, prepare a duration-scaled A1 exercise for the current session and label it `当次原创准备（非预置来源课程）`. Keep it separate from the audited curriculum: do not assign a material ID, source reference, or textbook-derived claim. If source-backed preparation is important to the learner, offer one of the six `audited_ready` scenes instead.

## Preparation card

Present, in this order:

1. language variety, scene, roles, and communication mission;
2. the full duration-scaled key-word recognition bank;
3. phrases or collocations;
4. complete sentence patterns;
5. register/politeness and one relevant culture or pronunciation note;
6. four story stages from the pack;
7. a measurable challenge.

Keep words, phrases, and sentence patterns visibly separate. A sentence pattern must remain a usable utterance, not a grammar label. Do not show a complete source dialogue.

## Scale by duration

Keep the source-backed active core compact, but make the learner-facing preview broad enough for real-world recognition and choices:

| Duration | Key words | Phrases | Sentence patterns | Challenge |
|---|---:|---:|---:|---|
| 5 min | 15 | 3 | 2 | independently use 2 selected active targets |
| 10 min | 20 | 5 | 3 | independently use 3 selected active targets |
| 20 min | 30 | 8 | 5 | complete all four story stages and use 5 active targets |
| 40 min | 40 | 12 | 8 | complete all stages, handle one complication, and transfer 2 patterns |

For custom durations, interpolate between the rows and never go below 15 key words. Keep the audited items and any session-original additions distinct internally: only the audited items carry material IDs, provenance, or mastery history. The broader vocabulary bank supports recognition and choice; it does not turn every word into an active role-play target.

Build vocabulary for practical coverage, not merely to hit a number. A café card should cover common drinks, hot/iced, cup sizes, milk and sweetener choices, strength or extra shots, dine-in/takeaway, and payment or pickup terms. Apply the same breadth test to every scene by covering the main things, actions, properties, options, and likely problems. Avoid near-duplicates and do not count inflected forms of one word as separate entries.

## Source behavior

The tool output includes provenance for internal use. Keep it out of the learner-facing card unless attribution or source inspection is requested. When requested, report source title, exact unit, usage role, and adaptation state. Never imply that `verification` material supplied the wording.
