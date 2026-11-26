"""Standard-Kontext mit allen konfigurierten Datenquellen."""
from app.agents.base import AgentContext
from app.sources.demo import DemoSource
from app.sources.keepa import KeepaSource

_demo = DemoSource()


def default_context() -> AgentContext:
    return AgentContext(sources={"keepa": KeepaSource(), "demo": _demo})
