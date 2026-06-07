# JFA Unify — CLAUDE.md

## Projecto

Plataforma multi-tenant de controlo de acesso. FastAPI backend + PostgreSQL (RLS) + Redis + MQTT + SvelteKit PWA + Tuya Hub 6E.

- **Python**: 3.15 (backend FastAPI + Uvicorn)
- **SvelteKit**: frontend PWA em `frontend/`
- **Porto**: a definir (produção ainda não deployada)

## Arquitectura

| Camada | Localização | Notas |
|--------|------------|-------|
| API | `backend/app/routers/` | devices, access, logs |
| Middleware | `backend/app/middleware/auth.py` | TenantAuthMiddleware — HMAC token |
| MQTT | `backend/app/services/mqtt_adapter.py` | TuyaAdapterAsync (Fase 1–2) / ESP32AdapterAsync (Fase 3) |
| Auth | `backend/app/services/auth.py` | HMAC-SHA256, token_expiry_seconds |
| Config | `backend/app/config.py` | Pydantic Settings + `@lru_cache` |
| BD | `backend/app/db/database.py` | SQLAlchemy 2.0 (PostgreSQL produção, SQLite em TESTING=1) |
| Migrations | `backend/alembic/versions/` | 3 versões: schema → RLS → indices |
| Suite | `backend/app/services/suite_client.py` | Integração JFA_Suite (gate: `suite_integration_enabled`) |

## Regras absolutas

- **PostgreSQL RLS**: `SET LOCAL app.current_tenant_id` é PostgreSQL-only — nunca usar em SQLite
- **TESTING=1 = SQLite**: testes unitários correm com SQLite; testes de integração requerem PostgreSQL real via `docker-compose.test.yml`
- **`@lru_cache` em `get_settings()`**: a fixture `mock_settings` no conftest deve chamar `get_settings.cache_clear()` — não assumir que pytest isola estado entre testes automaticamente
- **`suite_integration_enabled: False`** por defeito: não activar sem URL + token configurados no `.env`
- **Secrets**: `tuya_access_secret`, `secret_key`, tokens — nunca no chat; referenciar como `$SECRET_KEY`, `$ACCESS_SECRET`

## Build e Testes

```powershell
# Testes unitários (SQLite, rápidos — default)
cd C:\JFA_Unify\backend
$env:TESTING="1"; python -m pytest -q --tb=short
# → 225 passed, 36 deselected (integration/e2e/mqtt_broker excluídos por addopts)

# Lint
ruff check .
ruff format --check .

# Testes de integração RLS (requerem PostgreSQL)
# 1. Iniciar PostgreSQL efémero:
#    docker compose -f C:\JFA_Unify\docker-compose.test.yml up -d --wait
# 2. Correr:
#    python -m pytest -m integration -q --tb=short
# 3. Parar:
#    docker compose -f C:\JFA_Unify\docker-compose.test.yml down
```

**Markers pytest** (`pytest.ini`):
- `integration` — PostgreSQL real, `docker-compose.test.yml`
- `e2e` — Mosquitto real acessível
- `mqtt_broker` — broker MQTT real para load tests
- `unit` — mocks apenas

Por defeito (`addopts`): `not integration and not e2e and not mqtt_broker`

## Deploy

Infra de produção ainda não criada. O projecto não está no servidor ubuntu-50. Antes de deployar:
1. Criar `deploy/ubuntu-50/docker-compose.prod.yml`
2. Criar script `deploy-unify` análogo a `deploy-accesspay`
3. Configurar `.env` de produção (PostgreSQL externo ou container)
4. Configurar Cloudflare tunnel

## Integração JFA_Suite

Activar em `.env`:
```
SUITE_INTEGRATION_ENABLED=true
SUITE_BASE_URL=http://localhost:8040
SUITE_API_TOKEN=<token hmac>
```

Fluxo: `POST /access/` → verificar saldo Suite → `consume_token()` → grant MQTT → access log.

## Fases

| Fase | Escopo | Estado |
|------|--------|--------|
| Fase 1–2 | FastAPI + PostgreSQL RLS + MQTT Tuya | ✅ Implementado |
| Fase 3 | ESP32 adapter + BLE fallback + OTA | ⏳ Roadmap |
| Fase 4 | SvelteKit PWA completa | ⏳ Roadmap |

## GDPR / CNPD

- **CNPD deadline**: 30-Jun-2026 🔴
- DPIA Part 1 aguarda FA + advogado (call 13-Jun-2026)
- `_LEADS_RETENTION_DAYS` a confirmar em 13-Jun com advogado
