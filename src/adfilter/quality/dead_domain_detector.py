"""Dead domain detector — identifies rules targeting non-existent domains.

Uses async DNS resolution to check if domains are still active.
Dead domains bloat rule lists without providing any value.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class DomainCheckResult:
    """Result of a single domain check."""

    domain: str
    is_dead: bool
    reason: str = ""


class DeadDomainDetector:
    """Detect domains that no longer resolve to any address.

    Performs DNS lookups to identify dead domains.  Results can be used
    to prune stale rules from the output.
    """

    def __init__(
        self,
        *,
        timeout: float = 5.0,
        max_concurrency: int = 50,
        nameservers: list[str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.max_concurrency = max_concurrency
        self.nameservers = nameservers or []
        self._results: list[DomainCheckResult] = []

    async def check_domains(self, domains: list[str]) -> list[DomainCheckResult]:
        """Check a batch of domains for liveness."""
        sem = asyncio.Semaphore(self.max_concurrency)
        tasks = [self._check_one(domain, sem) for domain in domains]
        self._results = await asyncio.gather(*tasks)
        return self._results

    async def _check_one(self, domain: str, sem: asyncio.Semaphore) -> DomainCheckResult:
        """Check a single domain."""
        async with sem:
            try:
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.getaddrinfo(domain, None, family=socket.AF_UNSPEC),
                    timeout=self.timeout,
                )
                return DomainCheckResult(domain=domain, is_dead=False)
            except socket.gaierror, OSError:
                return DomainCheckResult(domain=domain, is_dead=True, reason="NXDOMAIN")
            except TimeoutError:
                return DomainCheckResult(domain=domain, is_dead=True, reason="timeout")
            except Exception as e:
                return DomainCheckResult(domain=domain, is_dead=True, reason=str(e))

    def get_dead_domains(self) -> list[str]:
        """Return the list of dead domains from the last check."""
        return [r.domain for r in self._results if r.is_dead]

    def get_live_domains(self) -> list[str]:
        """Return the list of live domains from the last check."""
        return [r.domain for r in self._results if not r.is_dead]

    @property
    def dead_count(self) -> int:
        return sum(1 for r in self._results if r.is_dead)

    @property
    def total_checked(self) -> int:
        return len(self._results)
