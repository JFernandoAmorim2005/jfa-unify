"""
Ponto de entrada da aplicação FastAPI — JFA Unify API.
Inicializa routers, middleware, MQTT e tratamento de erros.
"""
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.database import engine, Base, SessionLocal
from app.middleware.auth import TenantAuthMiddleware
from app.routers import devices, access, logs
from app.services.mqtt_adapter import (
    TuyaAdapterAsync,
    ESP32AdapterAsync,
    MQTTService,
)

settings = get_settings()
logger = logging.getLogger(__name__)

logging.basicConfig(level=getattr(logging, settings.log_level, logging.DEBUG))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida da aplicação: arranque e paragem."""
    logger.info("JFA Unify API a iniciar — ambiente: %s", settings.environment)
    # Criar tabelas (apenas em desenvolvimento; produção usa Alembic)
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)

    # Instanciar e iniciar MQTT adapter baseado na configuração
    mqtt_adapter = None
    mqtt_service = None
    try:
        if settings.mqtt_adapter_type.lower() == "esp32":
            logger.info("Inicializando ESP32AdapterAsync")
            mqtt_adapter = ESP32AdapterAsync(
                broker_url=f"mqtt://{settings.mqtt_broker}:{settings.mqtt_port}",
                client_id=f"{settings.mqtt_client_id}-{uuid.uuid4().hex[:8]}",
                ble_fallback_enabled=settings.mqtt_ble_fallback_enabled,
                local_cache_path=settings.mqtt_local_cache_path,
            )
        else:
            logger.info("Inicializando TuyaAdapterAsync")
            mqtt_adapter = TuyaAdapterAsync(
                broker_url=f"mqtt://{settings.mqtt_broker}:{settings.mqtt_port}",
                client_id=f"{settings.mqtt_client_id}-{uuid.uuid4().hex[:8]}",
                username=settings.mqtt_username,
                password=settings.mqtt_password,
            )

        mqtt_service = MQTTService(mqtt_adapter, SessionLocal)
        await mqtt_service.startup()
        app.state.mqtt_service = mqtt_service
        logger.info("MQTT service iniciado com sucesso")
    except Exception as e:
        logger.error("Erro ao iniciar MQTT service: %s", e)
        if mqtt_service:
            await mqtt_service.shutdown()
        raise

    yield

    # Paragem graceful do MQTT service
    if mqtt_service:
        try:
            await mqtt_service.shutdown()
            logger.info("MQTT service terminado")
        except Exception as e:
            logger.error("Erro ao terminar MQTT service: %s", e)

    logger.info("JFA Unify API a terminar.")


app = FastAPI(
    title="JFA Unify API",
    description="Backend de controlo de acessos multi-tenant com suporte Tuya Hub.",
    version="0.1.0",
    lifespan=lifespan,
)


async def get_mqtt_service() -> MQTTService:
    """Dependency injection para MQTTService."""
    return app.state.mqtt_service

# --- Middleware (ordem: CORS → Auth) ---
# NOTA: add_middleware aplica em ordem inversa (último adicionado = primeiro executado).
# TenantAuthMiddleware deve correr após CORS, por isso é adicionado primeiro.
app.add_middleware(TenantAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restringir em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Tratamento de erros global ---
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Erro não tratado: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor."},
    )


# --- Rotas de sistema ---
@app.get("/health", tags=["Sistema"])
async def health_check():
    """Verificação de estado da API."""
    mqtt_status = None
    try:
        mqtt_service = app.state.mqtt_service
        if mqtt_service:
            mqtt_status = await mqtt_service.get_status()
    except (AttributeError, Exception):
        pass

    return {
        "status": "ok",
        "environment": settings.environment,
        "mqtt": mqtt_status,
    }


# --- Routers de domínio ---
app.include_router(devices.router, prefix="/devices", tags=["Dispositivos"])
app.include_router(access.router, prefix="/access", tags=["Controlo de Acesso"])
app.include_router(logs.router, prefix="/logs", tags=["Auditoria"])
