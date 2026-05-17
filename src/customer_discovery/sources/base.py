from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, ClassVar

from customer_discovery.models.company import CompanyRecord


class CompanySource(ABC):
    source_id: ClassVar[str]

    @abstractmethod
    async def scrape(
        self,
        *,
        limit: int | None = None,
        **options: Any,
    ) -> AsyncIterator[CompanyRecord]:
        ...

    def validate_options(self, options: dict[str, Any]) -> dict[str, Any]:
        return options
