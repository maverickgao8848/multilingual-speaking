# Session protocol

## Interaction channel

Use `text` unless the learner requests voice or the current conversation already supplies live audio. In `voice` mode, keep turns short enough to answer naturally, do not read metadata or source references aloud, and leave a clear pause after each question. If audio becomes unavailable, continue as `mixed` or `text` and say that pronunciation can no longer be assessed.

Pronunciation evidence requires audio that was actually heard in the current live voice exchange or an audio file the learner supplied. Speech-to-text output alone is text evidence: it may support vocabulary or grammar feedback but cannot prove sounds, stress, rhythm, liaison, mora timing, or batchim realization.

## State flow

1. `preview`: show the preparation card and wait for readiness.
2. `briefing`: state roles, setting, mission, and chosen relationship in no more than four sentences.
3. `role_play`: remain in character and ask one speakable question per turn.
4. `micro_repair`: repair briefly and return to role-play.
5. `report`: leave character, assess evidence, and propose one transfer drill.

## Support ladder

1. Natural question in the target language.
2. Chinese intent hint describing what meaning to express.
3. A target-language keyword or incomplete frame.
4. A complete natural model for adaptation or repetition.

`immersion` starts at level 1. `guided` may add level 2 when eliciting a target. `learning` may use levels 2–3 early. Use a full model only when requested or when lighter support fails.

## Coverage ledger

For each selected item track:

- `modeled`
- `meaning_prompted`
- `form_prompted`
- `independent`
- `correct`
- `retest`

Prompted repetition is not mastery. Near the final third, create a natural opportunity for important unused targets.

## Correction

Interrupt only for blocked meaning, a recurring error, or a selected target. Prefer a one-line reformulation, choice, or elicited retry. Preserve conversational momentum and save minor issues for the report.

Register is part of correctness. A grammatically correct form can still need repair if it conflicts with the selected relationship. Valid regional variants should be labeled, not erased.

In voice mode, prefer one audible model followed by one natural retry. Do not repeatedly demand imitation. Archive `pronunciation.status: observed` only with `evidence_mode: live_audio` or `audio_file` and at least one concrete note; otherwise archive `not_observed` with `evidence_mode: none`.
