"""Record/replay wrapper keyed by a hash of the request, for deterministic tests and CI."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from trusted_service_agent.llm.base import LLMClient, LLMRequest, LLMResponse


class CassetteMiss(KeyError):
    def __init__(self, key: str, purpose: str) -> None:
        super().__init__(f"no cassette entry for {purpose} ({key[:12]}); run `make record`")
        self.key, self.purpose = key, purpose


def request_key(req: LLMRequest) -> str:
    payload = {
        "model": req.model,
        "system": req.system,
        "messages": [m.model_dump() for m in req.messages],
        "tools": [t.model_dump() for t in req.tools],
        "tool_mode": req.tool_mode,
        "allowed_tools": req.allowed_tools,
        "schema_name": req.response_schema.__name__ if req.response_schema else None,
        "temperature": req.temperature,
        "thinking_level": req.thinking_level,
        "max_output_tokens": req.max_output_tokens,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class CassetteClient:
    """`record` reuses recorded responses, appends new ones; `replay` serves the first recording."""

    def __init__(
        self, path: Path, mode: Literal["record", "replay"], inner: LLMClient | None = None
    ) -> None:
        self.path, self.mode, self.inner = path, mode, inner
        self.entries: dict[str, list[dict]] = {}
        self.served: dict[str, int] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                entry = json.loads(line)
                self.entries.setdefault(entry["key"], []).append(entry)

    async def aclose(self) -> None:
        if close := getattr(self.inner, "aclose", None):
            await close()

    async def generate(self, req: LLMRequest) -> LLMResponse:
        key = request_key(req)
        if self.mode == "replay":
            if key not in self.entries:
                raise CassetteMiss(key, req.purpose)
            self.served[key] = self.served.get(key, 0) + 1
            entry = self.entries[key][0]  # identical request → identical response
            return LLMResponse.model_validate(entry["response"]).model_copy(
                update={"source": "cassette"}
            )
        if key in self.entries:
            return LLMResponse.model_validate(self.entries[key][0]["response"])
        assert self.inner is not None, "record mode needs an inner client"
        resp = await self.inner.generate(req)
        entry = {"key": key, "purpose": req.purpose, "response": resp.model_dump()}
        self.entries.setdefault(key, []).append(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return resp
