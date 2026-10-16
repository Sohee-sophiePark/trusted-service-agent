import pytest

from trusted_service_agent.config import settings
from trusted_service_agent.llm.base import LLMResponse
from trusted_service_agent.llm.gateway import Gateway
from trusted_service_agent.llm.limiter import RateLimiter
from trusted_service_agent.llm.scripted import ScriptedClient


@pytest.fixture
def scripted():
    return ScriptedClient()


@pytest.fixture
def gw(scripted):
    s = settings()
    return Gateway(s, scripted, RateLimiter(s.rate_limits, s.retry, s.timeout_seconds))


def reply(**parsed) -> LLMResponse:
    return LLMResponse(parsed=parsed)
