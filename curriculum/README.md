# Bundled multilingual curriculum

This directory contains the complete audited runtime curriculum used by `multilingual-speaking`:

- `sample-packs.json` contains all 30 A1 language-and-scene packs.
- `target-extensions.json` contains source-aware keyword and phrase expansions used by 20- and 40-minute cards.
- `scene-map.json` contains the supported scenes and source coverage.
- `sources.json` contains the multilingual source and license registry.
- `topic-catalog.json` distinguishes 6 audited, ready-to-use scenes from 20 on-demand original practice topics available in each supported language.
- `manifest.json` records integrity hashes for the four runtime data files.

No parent-directory curriculum is required. Run the following command from any working directory to verify the bundled copy:

```text
python <skill-directory>/scripts/sync_curriculum.py --check
```

Repository maintainers can compare or refresh the bundle only by explicitly supplying an authoring source:

```text
python <skill-directory>/scripts/sync_curriculum.py --source-root <authoring-curriculum> --check
python <skill-directory>/scripts/sync_curriculum.py --source-root <authoring-curriculum>
```
