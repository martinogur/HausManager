"""Celery-Worker + Beat-Zeitplan. Jeder Job ist per Redis-Lock gegen Parallelläufe geschützt."""
from __future__ import annotations

import logging
from contextlib import contextmanager

import redis
from celery import Celery
from celery.schedules import crontab

from app.agents.base import run_agent
from app.agents.growth import GrowthAgent
from app.agents.master import MasterAgent
from app.agents.publishing import PriceWatchAgent, PublisherAgent
from app.agents.registry import default_context
from app.bootstrap import bootstrap
from app.config import get_settings
from app.db import SessionLocal
from app.logging_setup import setup_logging

s = get_settings()
celery = Celery("dealfehler", broker=s.redis_url, backend=s.redis_url)
celery.conf.update(
    timezone=s.timezone, task_acks_late=True, worker_prefetch_multiplier=1, task_time_limit=900,
    task_soft_time_limit=840, broker_connection_retry_on_startup=True,
    beat_schedule={
        "master-cycle": {"task": "dealfehler.master", "schedule": 600.0},  # alle 10 min
        "publisher": {"task": "dealfehler.publisher", "schedule": 60.0},  # jede Minute
        "price-watch": {"task": "dealfehler.price_watch", "schedule": 900.0},  # alle 15 min
        "growth": {"task": "dealfehler.growth", "schedule": crontab(hour=4, minute=17)},
    },
)
log = logging.getLogger(__name__)


@contextmanager
def single_run(name: str, ttl: int = 900):
    r = redis.Redis.from_url(s.redis_url)
    lock = r.lock(f"dealfehler:lock:{name}", timeout=ttl, blocking=False)
    got = lock.acquire(blocking=False)
    try:
        yield got
    finally:
        if got:
            try:
                lock.release()
            except redis.exceptions.LockError:
                pass


def _run(agent_cls, lock_name: str) -> dict:
    with single_run(lock_name) as ok:
        if not ok:
            return {"skipped": "läuft bereits"}
        with SessionLocal() as db:
            run = run_agent(db, agent_cls(), default_context())
            return {"status": run.status, "stats": run.stats}


@celery.on_after_configure.connect
def _setup(sender, **_):
    setup_logging()
    with SessionLocal() as db:
        bootstrap(db)


@celery.task(name="dealfehler.master")
def master_task():
    return _run(MasterAgent, "master")


@celery.task(name="dealfehler.publisher")
def publisher_task():
    return _run(PublisherAgent, "publisher")


@celery.task(name="dealfehler.price_watch")
def price_watch_task():
    return _run(PriceWatchAgent, "price_watch")


@celery.task(name="dealfehler.growth")
def growth_task():
    return _run(GrowthAgent, "growth")
