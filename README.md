# Agile Team Simulator

A minimal FastAPI + vanilla JS webapp where a human Product Owner participates with an agile software team. Other roles (PM, Architect, QA, DevOps, Backend, Frontend) are simulated to progress goals.

## Features
- Create goals/backlog items as Product Owner
- Live team chat via WebSocket
- Real-time backlog updates as roles progress work
- Simple dark UI, no build step

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000`.

## API
- `GET /` - UI
- `GET /roles` - Available roles
- `GET /state` - Current state snapshot
- `POST /message` - Send a chat message `{sender, role, text}`
- `POST /goals` - Create a goal `{title, description}`
- `WS /ws` - Real-time events `init`, `chat`, `backlog_update`

## Notes
- State is in-memory and resets on restart
- This is a demo; no auth and open CORS for local use
