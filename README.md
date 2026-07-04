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

NVIDIA NIM can be used instead of OpenAI. It works from supplied source URLs and does not perform independent web search:

```powershell
$env:NVIDIA_API_KEY="..."
.\.venv\Scripts\python -m content_factory.cli run examples/courtroom.json --provider nvidia --reset
```

The default NVIDIA model is `z-ai/glm-5.2`; override it with `NVIDIA_MODEL`.

## Safety boundaries

- Demo content is visibly blocked from publication.
- Live research uses web search and a claim ledger; a human still owns factual verification.
- Visuals carry provenance labels (`generated`, `stock`, `archival`, or `reconstruction`).
- Distribution output is draft-only. The factory does not silently publish.
- Provider calls are isolated; HyperGen/HeyGen, OpenAI, voice, rendering, and publishing can be replaced independently.

See [docs/FACTORY_BLUEPRINT.md](docs/FACTORY_BLUEPRINT.md) and [config/channel.json](config/channel.json).

## Fly.io deployment

The repository includes an explicit `Dockerfile` and `fly.toml`. Create the volume once, set runtime secrets, and deploy:

```powershell
fly volumes create contentfactory_data --region ams --size 10 --app contentfactory
fly secrets set API_TOKEN="replace-with-a-long-random-token" --app contentfactory
fly secrets set NVIDIA_API_KEY="your-new-nvidia-key" --app contentfactory
fly deploy --app contentfactory
```

Start an episode with `POST /api/v1/episodes`, inspect it with `GET /api/v1/episodes/{case_id}`, and approve each gate with `POST /api/v1/episodes/{case_id}/approvals/{stage}`. Send `Authorization: Bearer <API_TOKEN>` on all API requests. `GET /health` is public.

The production Docker image also builds the React dashboard. Open the Fly app URL, enter `API_TOKEN` once, and the backend exchanges it for an eight-hour HttpOnly session cookie. The token is not stored in browser JavaScript storage.
