from __future__ import annotations

import json
import os
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is required for LLM stages")

    def complete_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: type[T],
    ) -> T:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("Install openai: pip install openai") from e

        client = OpenAI(api_key=self._api_key)
        schema_dict = schema.model_json_schema()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema_dict,
                    "strict": False,
                },
            },
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        return schema.model_validate(data)

    def complete_text(
        self,
        *,
        model: str,
        system: str,
        user: str,
    ) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("Install openai: pip install openai") from e

        client = OpenAI(api_key=self._api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""


class MockLLMClient:
    """For tests — returns pre-set responses by stage key."""

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self._responses = responses or {}

    def complete_json(self, *, model: str, system: str, user: str, schema: type[T]) -> T:
        key = schema.__name__
        if key not in self._responses:
            raise KeyError(f"No mock response for {key}")
        return schema.model_validate(self._responses[key])

    def complete_text(self, *, model: str, system: str, user: str) -> str:
        return self._responses.get("text", "")
