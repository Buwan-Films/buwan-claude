---
name: proof-gate
description: The Buwan proof gate — measures every cut in an EDL against the house pacing targets (wedding bursts and holds, corporate steady cutting) and gives PASS / FAIL with fixes. Use after a rough cut or any recut, before audio polish, or when an editor asks "check pacing" or "run the proof gate".
argument-hint: "<path to .edl> [wedding|corporate] [speech|cut]"
---

# Proof gate

Run the measurement script, then interpret it. Arguments: $ARGUMENTS

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/proof-gate.js" <file.edl> --type <wedding|corporate> --mode <speech|cut>
```

- Infer `--type` from the project folder name (`_wedding` / `_corporate`) if not given.
- `--mode speech` = the Story-Lock selects EDL (speech only). It checks structure: total length, 4-part timing when part markers exist, and that no line is cut mid-word (event shorter than 0.5s).
- `--mode cut` = the picture cut with b-roll (export the V1/picture track as CMX3600 from the app). It checks the pacing targets.

The script prints measurements and a verdict per rule. Report them as a table: rule · target · measured · PASS/FAIL · fix. For each FAIL, point to the exact events (record TC) to fix. "On beat and on words" can't be measured from an EDL — say so and ask the editor to confirm by eye in review, or check against a beat-marker list if one exists in `edit/`.

The gate passes only when every rule passes, or the editor writes an override reason, which you add to the paper edit under **Gate overrides**.
