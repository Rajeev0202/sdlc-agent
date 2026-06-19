# Redis Cache Setup for SDLC Agent

The SDLC agent supports a persistent Redis cache for LLM responses. Caching survives server restarts and can reduce demo costs by ~100% on repeat runs.

## Quick Start (Choose ONE)

### Option 1: Docker (recommended, cross-platform)

```bash
docker compose up -d redis
```

Verify it's running:
```bash
docker ps
```

To stop:
```bash
docker compose down
```

### Option 2: Memurai on Windows

Memurai is a Redis-compatible drop-in for Windows.

```powershell
winget install Memurai.Memurai-Developer
```

The service starts automatically on port 6379.

### Option 3: WSL Ubuntu

```bash
wsl --install -d Ubuntu
# inside WSL:
sudo apt update && sudo apt install redis-server -y
sudo service redis-server start
```

### Option 4: Redis Cloud (managed, free tier available)

1. Sign up at https://redis.com/try-free/
2. Create a free DB (30 MB is plenty for cache)
3. Copy the connection string

---

## Connect the SDLC Agent

Once Redis is running, add this to your `.env`:

```env
REDIS_URL=redis://localhost:6379/0
LLM_CACHE_TTL=86400
```

For Redis Cloud:
```env
REDIS_URL=redis://default:<password>@<host>:<port>
```

---

## Restart the Server

```bash
python -m sdlc_agent.web.app
```

Look for this in the logs:
```
[LLM Cache] Connected to Redis at redis://localhost:6379/0
[LLM Cache] Backend: redis
```

---

## Verify Cache is Working

```bash
python -c "import requests, json; print(json.dumps(requests.get('http://127.0.0.1:5002/api/cost-stats').json(), indent=2))"
```

Expected output (after Redis is configured):
```json
{
  "cache_backend": "redis",
  "redis_configured": true,
  ...
}
```

---

## Cache Commands

| Action | Command |
|---|---|
| View stats | `GET /api/cost-stats` |
| Clear cache | `POST /api/cost-stats/clear` |
| Inspect keys | `redis-cli KEYS "sdlc:llm:*"` |
| Wipe all | `redis-cli FLUSHDB` |

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `REDIS_URL` | unset | Connection string; if unset, uses in-memory cache |
| `LLM_CACHE_TTL` | `86400` (24h) | Cache entry TTL in seconds |

---

## Without Redis

The agent works perfectly fine without Redis — it uses an in-memory cache that's lost on restart. Redis is only needed if you:
- Run the demo multiple times back-to-back
- Restart the server frequently
- Have multiple agent workers sharing cache
- Want to track cumulative cost savings over days
