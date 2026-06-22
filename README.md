# DocumentChecker

Docker Compose
```bash
cp .env.example .env
docker compose up --build
```

Frontend: http://127.0.0.1:8000
Backend/OpenAPI through Nginx: http://127.0.0.1:8000/docs

Docker Compose (production, Nginx frontend)
```bash
cp .env.example .env
docker compose -f docker-compose.prod.yml up --build
```

Production entrypoint for the host Traefik: http://127.0.0.1:8000
Public site: https://doctest.freeddns.org
Backend/OpenAPI through Nginx: https://doctest.freeddns.org/docs

For production, Traefik should terminate HTTPS for `doctest.freeddns.org` and forward traffic to `127.0.0.1:8000`. The Docker production stack publishes only Nginx on that loopback address; Nginx serves the built frontend static files and proxies backend routes to the internal `backend:8000` service.

Keep the frontend API URL relative so Nginx proxies it:
```env
APP_BIND_ADDRESS=127.0.0.1
APP_PORT=8000
VITE_API_BASE_URL=/api
```

Models are configured in `models.yaml`, not in `.env`:
```yaml
default_model: gpt-oss:120b-cloud

endpoints:
  - id: ollama-cloud
    url: https://ollama.com/api/chat
    api_format: ollama
    api_key_env: OLLAMA_API_KEY

  - id: openai-compatible
    base_url: https://api.openai.com/v1
    api_format: openai
    api_key_env: OPENAI_API_KEY

  - id: nanogpt
    base_url: https://nano-gpt.com/api/v1
    api_format: nanogpt
    api_key_env: NANOGPT_API_KEY

models:
  - id: gpt-oss:120b-cloud
    request_model: gpt-oss:120b
    endpoint: ollama-cloud
    name: GPT OSS 120B Cloud
    description: Default cloud model for document checks.
    usage_limit: 100
    rate_limit: 5
    context_window_tokens: 131072
```

`usage_limit` is the per-user number of checks allowed for the model. Use an empty value or omit it for an unlimited model. `rate_limit` is the per-process requests-per-minute limit for that model; use `0` to disable throttling. `context_window_tokens` is the model context length used to trim oversized documents before sending them to the LLM. You can also use `context_window`, `max_context_tokens`, or `max_context_window` as aliases. Context length priority is: model setting, `LLM_CONTEXT_WINDOW_TOKENS`, API metadata, then model family defaults. `endpoints` can contain multiple LLM API URLs; every model can reference one endpoint with `endpoint`, and every endpoint can read its own key from `.env` through `api_key_env`.

For Ollama Cloud direct API access, set the key in `.env`:
```env
OLLAMA_API_KEY=ollama-...
```

The public model id shown to users can stay `gpt-oss:120b-cloud`, while `request_model: gpt-oss:120b` is sent to `https://ollama.com/api/chat`.

For NanoGPT, generate an API key at `https://nano-gpt.com/api`, set it in `.env`, and add models to `models.yaml` with `endpoint: nanogpt`:
```env
NANOGPT_API_KEY=...
```
```yaml
  - id: nanogpt/minimax-m2.7
    request_model: minimax/minimax-m2.7
    endpoint: nanogpt
    name: NanoGPT Minimax M2.7
    description: NanoGPT OpenAI-compatible model
    usage_limit: 5
    context_window_tokens: 1000000
```

NanoGPT uses an OpenAI-compatible chat completions API at `https://nano-gpt.com/api/v1/chat/completions`; `request_model` should match the model id returned by NanoGPT, for example `minimax/minimax-m2.7`.

Predefined `.docx`, `.md`, and `.markdown` templates can be placed into the `doctempletes` folder. Administrators can also upload templates from the web UI. The backend lists them through `/api/templates`, and users can select one instead of uploading a template file.

Bibliography checks can flag probably fabricated references without paid catalog APIs. The backend extracts bibliography records with the `bibliography_model` configured in `models.yaml`, then verifies records against free public indexes: Crossref, OpenAlex, Semantic Scholar, Google Books, and Open Library.

```yaml
default_model: gpt-oss:120b-cloud
bibliography_model: openai/gpt-5-nano
```

```http
POST /api/bibliography/check
{
  "document_content": "...",
  "max_references": 30
}
```

For files, use `POST /api/bibliography/check-upload` with `document_file` and optional `max_references`. Supported files are `.docx`, `.txt`, `.md`, and `.markdown`. Results use `confirmed`, `probable`, `suspicious`, `not_found`, or `unparsed`; `suspicious` and `not_found` are review flags, not definitive proof that a source is fake.

Administrators are configured in `.env`:
```env
ADMIN_LOGINS=admin@example.com,second-admin@example.com
```

Separate administrator logins with commas, semicolons, spaces, or new lines. Admin users have unlimited checks. They can reset usage counters from the UI or through `POST /api/admin/usage/reset`, and can set the number of checks available to a user through `POST /api/admin/usage/limit`. The custom available checks value may be greater than the model `usage_limit` in `models.yaml`.

Usage counters can also be reset automatically every N hours. Configure the interval in `.env`:
```env
USAGE_LIMIT_RESET_INTERVAL_HOURS=24
```
Use `0` or an empty value to disable automatic resets.

By default the backend calls an Ollama-compatible API on the host:
`http://host.docker.internal:11434/api/chat`.

For an OpenAI-compatible API, set these values in `.env`:
```env
LLM_API_URL=
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_API_FORMAT=openai
AI_PROXY_KEY=sk-...
LLM_REQUESTS_PER_MINUTE=0
```

Those legacy `LLM_API_*` values are still supported for models without an endpoint in `models.yaml`.

For Timeweb AI Proxy:
```env
LLM_API_URL=
LLM_API_BASE_URL=https://api.timeweb.ai/v1
LLM_API_FORMAT=openai
AI_PROXY_KEY=<YOUR_AI_PROXY_KEY>
LLM_REQUESTS_PER_MINUTE=0
```

Backend (Python/FastAPI)
```bash
pip install -r requirements.txt
python src/app/main.py
```

Frontend (Vue)
```bash
cd apps/search
npm install
npm run dev
```
