# API Local Run — M3 Skeleton

The M3 milestone ships a deployable HTTP shell with **no
database requirements**, **no authentication**, and **no
query-answer path**. Use this guide to launch it locally.

## Launch Contract

```bash
uvicorn src.api.app:create_app --factory
```

Equivalent launchers expose the same factory:

```bash
# use python -m:
python -m src.api
```

`python -m src.api` reads the same `Settings` and runs uvicorn
under the listed host/port/log-level.

## Configuration

M3 ships only the three runtime tunables the skeleton needs.
Set them via environment variables, all with the
`SAGEWELL_` prefix.

| Env var | Default |
|---|---|
| `SAGEWELL_LOG_LEVEL` | `INFO` |
| `SAGEWELL_API_HOST`  | `127.0.0.1` |
| `SAGEWELL_API_PORT`  | `8000` |

### Example

```bash
SAGEWELL_API_HOST=0.0.0.0 SAGEWELL_API_PORT=8000 \
    uvicorn src.api.app:create_app --factory
```

## Route Surface

| Path | Description |
|---|---|
| `GET /health` | Liveness. Returns `200` with `{"status":"ok"}`. |
| `GET /openapi.json` | Generated OpenAPI 3.1 document. |
| `GET /docs` | Swagger UI. |
| `GET /redoc` | ReDoc UI. |

## Correlation IDs

Every request is wrapped in a pure-ASGI middleware that reads
or generates the `X-Correlation-ID` header. Supply one if you
need request tracing; otherwise a fresh UUID4 is generated.

```bash
curl -H "X-Correlation-ID: my-trace-id" \
     http://127.0.0.1:8000/health
# 200 -> response carries back X-Correlation-ID: my-trace-id
```

## Error Envelope

Errors return the canonical V1 envelope:

```json
{
  "code": "internal_error",
  "message": "An unexpected error occurred.",
  "correlation_id": "..."
}
```

- Validation errors → `422` with `code: "validation_error"`.
- Uncaught exceptions → `500` with `code: "internal_error"`,
  logged at ERROR with keys `correlation_id`, `exception_type`,
  `exc_message`.

## Inputs Required to Run

- None. Bring-up runs without `SAGEWELL_DB_URL`.

## Input This Layer Does NOT Consume

- `SAGEWELL_DB_URL` — owned by a future Postgres lifespan hook.
- `SAGEWELL_CORS_ALLOWED_ORIGINS` — out of M3.
- `SAGEWELL_TRUSTED_PROXY_HEADER` — out of M3.
- JWT / auth secret settings — owned by M5.

## Test Surface

```bash
.venv\Scripts\python.exe -m pytest -q tests/api
```
