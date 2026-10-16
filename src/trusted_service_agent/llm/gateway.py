"""Every model call goes here: role → model chain, limiter, live fallback, call count."""

from pydantic import BaseModel

from trusted_service_agent.config import Settings
from trusted_service_agent.llm.base import LLMClient, LLMRequest, Message, RetryableLLMError
from trusted_service_agent.llm.cassette import CassetteMiss
from trusted_service_agent.llm.limiter import RateLimiter


class Gateway:
    def __init__(self, settings: Settings, client: LLMClient, limiter: RateLimiter) -> None:
        self.settings, self.client, self.limiter = settings, client, limiter
        self.calls = 0
        self.exhausted: set[str] = set()

    async def ask(self, role: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        """JSON matching `schema` from the newest available model in the role's chain.

        Live/record fall back on quota, overload or timeout (429/503/408); replay takes the first
        model with a recording, so the model that actually served is the one replayed."""
        chain = self.settings.models[role]
        models = [m for m in chain if m not in self.exhausted] or chain[-1:]
        for i, model in enumerate(models):
            req = LLMRequest(
                model=model,
                system=system,
                messages=[Message(role="user", text=user)],
                temperature=self.settings.temperature[role],
                max_output_tokens=self.settings.max_output_tokens[role],
                thinking_level=self.settings.thinking_level[role]
                if model.startswith("gemini-3")
                else 0,
                response_schema=schema,
                purpose=role,
            )
            try:
                self.calls += self.settings.run_mode != "replay"
                if self.settings.run_mode == "replay":
                    resp = await self.client.generate(req)  # no network, no rate limit
                else:
                    resp = await self.limiter.call(model, lambda _n, r=req: self.client.generate(r))
                self.calls += self.settings.run_mode == "replay"
                return schema.model_validate(resp.parsed)
            except CassetteMiss:
                if i == len(models) - 1:
                    raise
            except RetryableLLMError as e:
                if i == len(models) - 1 or e.status not in (408, 429, 503):
                    raise
                self.exhausted.add(model)
        raise AssertionError("unreachable")
