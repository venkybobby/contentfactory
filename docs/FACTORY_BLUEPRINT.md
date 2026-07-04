# Content Factory Blueprint

## Production line

1. **Intake** — URL/case, audience, angle, format, deadline.
2. **Research** — collect primary sources first; create claim-level evidence ledger.
3. **Editorial gate** — human approves facts, framing, and risk notes.
4. **Writing** — 8–10 minute documentary script with citations and timing.
5. **Pre-production** — scenes, shot list, host lines, B-roll, graphics, SFX, and HyperGen prompts.
6. **Generation** — voice, licensed/generated visuals, music, and scene clips through replaceable providers.
7. **Assembly** — timeline, captions, loudness normalization, brand intro/outro.
8. **QA gate** — factual, visual, audio, caption, rights, and brand checks.
9. **Distribution** — YouTube package, Reel, X thread, LinkedIn article; publish only after approval.
10. **Learning loop** — retention, CTR, watch time, comments, and corrections feed the next brief.

## Agent roles

| Agent | Owns | Cannot do |
|---|---|---|
| Producer | Workflow state, budget, retries | Approve its own output |
| Researcher | Sources, claims, contradictions | Invent missing facts |
| Fact checker | Claim/source coverage | Rewrite evidence |
| Writer | Narrative and narration | Remove citation IDs |
| Director | Scenes and visual continuity | Depict reconstructions as archival fact |
| Renderer | Provider jobs and assets | Publish |
| QA editor | Automated checks and review packet | Override human gate |
| Distributor | Metadata and scheduled upload | Publish without approval token |

## Artifact contract

Each run is immutable and resumable. Every stage writes one JSON artifact with its inputs, outputs, provider/model version, timestamps, and approval state. Failed stages can retry without regenerating approved work.

Minimum artifacts: `intake.json`, `research.json`, `evidence.json`, `script.json`, `scenes.json`, `render.json`, `qa.json`, and `distribution.json`.

## Evidence policy

- Prefer court records, regulator releases, company statements, and original research.
- Store an exact locator for every source (URL plus page/paragraph/timestamp where possible).
- Label visuals as archival, licensed stock, generated, or reconstruction.
- Block script lock when a material factual claim has no source.
- Record corrections; never overwrite the historical evidence ledger.

## Provider boundaries

HyperGen, a voice service, an image model, FFmpeg, and publishing APIs belong behind adapters. The pipeline owns editorial truth and workflow state; vendors only perform bounded generation/rendering jobs.

## MVP milestones

1. Resumable local orchestrator and approval gates.
2. Research + script provider with citation validation.
3. HyperGen export adapter and asset manifest.
4. FFmpeg assembly, captions, and QA report.
5. YouTube draft upload and analytics feedback.

