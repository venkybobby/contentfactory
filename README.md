# The AI Confession — Agentic Content Factory

One case brief becomes a complete evidence-first documentary package: research ledger, script, scene plan, HyperGen prompts, narration, captions, 1080p preview video, QA report, thumbnail brief, YouTube metadata, Reel, X thread, LinkedIn article, and analytics manifest.

## Run the complete factory

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m content_factory.cli run examples/courtroom.json --provider demo --auto-approve --reset
```

The rendered video and all artifacts appear in `runs/AIC-0002/`. Demo mode creates a production-flow preview and blocks public publishing because its narrative is not source-verified.

For live, web-researched editorial output:

```powershell
$env:OPENAI_API_KEY="..."
.\.venv\Scripts\python -m content_factory.cli run examples/courtroom.json --provider openai --reset
```

Production runs stop at three gates. Inspect the artifacts, then resume:

```powershell
.\.venv\Scripts\python -m content_factory.cli approve AIC-0002 editorial_approval --by Venky
.\.venv\Scripts\python -m content_factory.cli run examples/courtroom.json --provider openai
```

Repeat for `script_approval` and `final_approval`. `--auto-approve` exists for local end-to-end testing only.

## Safety boundaries

- Demo content is visibly blocked from publication.
- Live research uses web search and a claim ledger; a human still owns factual verification.
- Visuals carry provenance labels (`generated`, `stock`, `archival`, or `reconstruction`).
- Distribution output is draft-only. The factory does not silently publish.
- Provider calls are isolated; HyperGen/HeyGen, OpenAI, voice, rendering, and publishing can be replaced independently.

See [docs/FACTORY_BLUEPRINT.md](docs/FACTORY_BLUEPRINT.md) and [config/channel.json](config/channel.json).
