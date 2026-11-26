from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text

from app import __version__
from app.api import admin, channel_kit, public
from app.bootstrap import bootstrap
from app.config import get_settings
from app.db import SessionLocal
from app.logging_setup import setup_logging
from app.models import AgentState, Deal, ErrorLog, PlatformState, Publication


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    with SessionLocal() as db:
        bootstrap(db)
    yield


def create_app() -> FastAPI:
    s = get_settings()
    if s.app_env == "production" and s.secret_key.startswith("dev-"):
        raise RuntimeError("SECRET_KEY muss in Produktion gesetzt sein")
    app = FastAPI(title="DealFehler API", version=__version__, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in s.cors_origins.split(",") if o.strip()],
                       allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
    app.include_router(admin.router)
    app.include_router(public.router)
    app.include_router(channel_kit.router)
    if s.storage_backend == "local":
        Path(s.media_dir).mkdir(parents=True, exist_ok=True)
        app.mount("/media", StaticFiles(directory=s.media_dir), name="media")

    @app.get("/healthz")
    def healthz():
        out = {"version": __version__, "db": False, "redis": None}
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            out["db"] = True
        try:
            import redis

            out["redis"] = bool(redis.Redis.from_url(s.redis_url, socket_timeout=2).ping())
        except Exception:
            out["redis"] = False
        return out

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics():
        """Prometheus-Format (ohne Zusatzbibliothek)."""
        lines = []
        with SessionLocal() as db:
            for st, n in db.execute(select(Deal.status, func.count()).group_by(Deal.status)).all():
                lines.append(f'dealfehler_deals{{status="{st.value}"}} {n}')
            for pf, st, n in db.execute(select(Publication.platform, Publication.status, func.count())
                                        .group_by(Publication.platform, Publication.status)).all():
                lines.append(f'dealfehler_publications{{platform="{pf.value}",status="{st.value}"}} {n}')
            for p in db.scalars(select(PlatformState)).all():
                lines.append(f'dealfehler_platform_kill_switch{{platform="{p.platform}"}} {int(p.kill_switch)}')
                lines.append(f'dealfehler_platform_consecutive_errors{{platform="{p.platform}"}} {p.consecutive_errors}')
            for a in db.scalars(select(AgentState)).all():
                lines.append(f'dealfehler_agent_consecutive_failures{{agent="{a.name}"}} {a.consecutive_failures}')
            n = db.scalar(select(func.count()).select_from(ErrorLog).where(ErrorLog.resolved.is_(False))) or 0
            lines.append(f"dealfehler_unresolved_errors {n}")
            lines.append(f"dealfehler_dry_run {int(s.dry_run)}")
        return "\n".join(lines) + "\n"

    return app


app = create_app()
