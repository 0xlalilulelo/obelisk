"""Token and USD cost tracking. Always on; printed after every agent response.

Pricing is per-model and per-million-tokens, and accounts for prompt caching
(cache writes cost more than fresh input; cache reads cost far less). Rates are
constants here so they are trivial to update — see Anthropic's pricing page:
https://www.anthropic.com/pricing
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelPricing:
    """USD per million tokens."""

    input: float
    output: float
    cache_write_5m: float
    cache_read: float


# Per-MTok rates. Sonnet/Opus/Haiku tiers as published; update if rates change.
PRICING: dict[str, ModelPricing] = {
    "claude-sonnet-4-6": ModelPricing(input=3.0, output=15.0, cache_write_5m=3.75, cache_read=0.30),
    "claude-sonnet-4-5": ModelPricing(input=3.0, output=15.0, cache_write_5m=3.75, cache_read=0.30),
    "claude-opus-4-8": ModelPricing(input=15.0, output=75.0, cache_write_5m=18.75, cache_read=1.50),
    "claude-opus-4-6": ModelPricing(input=15.0, output=75.0, cache_write_5m=18.75, cache_read=1.50),
    "claude-haiku-4-5": ModelPricing(input=1.0, output=5.0, cache_write_5m=1.25, cache_read=0.10),
}

_DEFAULT_PRICING = ModelPricing(input=3.0, output=15.0, cache_write_5m=3.75, cache_read=0.30)
_PER_MILLION = 1_000_000.0


def pricing_for(model: str) -> ModelPricing:
    """Resolve pricing for a model id, falling back to the Sonnet tier."""
    return PRICING.get(model, _DEFAULT_PRICING)


@dataclass(frozen=True)
class CallCost:
    """The cost of a single API call."""

    label: str
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    usd: float
    latency_s: float


@dataclass
class CostTracker:
    """Accumulates per-call costs and the running USD total for a session."""

    model: str
    calls: list[CallCost] = field(default_factory=list)

    def record(
        self,
        *,
        label: str,
        input_tokens: int,
        output_tokens: int,
        cache_write_tokens: int = 0,
        cache_read_tokens: int = 0,
        latency_s: float = 0.0,
    ) -> CallCost:
        """Compute and store the cost of one call; returns the CallCost."""
        p = pricing_for(self.model)
        usd = (
            input_tokens * p.input
            + output_tokens * p.output
            + cache_write_tokens * p.cache_write_5m
            + cache_read_tokens * p.cache_read
        ) / _PER_MILLION
        call = CallCost(
            label=label,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_write_tokens=cache_write_tokens,
            cache_read_tokens=cache_read_tokens,
            usd=usd,
            latency_s=latency_s,
        )
        self.calls.append(call)
        return call

    @property
    def total_usd(self) -> float:
        return sum(c.usd for c in self.calls)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens + c.cache_read_tokens + c.cache_write_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def max_latency_s(self) -> float:
        return max((c.latency_s for c in self.calls), default=0.0)

    def format_last_call(self) -> str:
        if not self.calls:
            return "(no API calls yet)"
        c = self.calls[-1]
        return (
            f"[cost] {c.label}: in={c.input_tokens} out={c.output_tokens} "
            f"cache_r={c.cache_read_tokens} cache_w={c.cache_write_tokens} "
            f"| ${c.usd:.4f} this call | ${self.total_usd:.4f} session total "
            f"| {c.latency_s:.1f}s"
        )

    def format_summary(self) -> str:
        lines = [
            "",
            "=" * 64,
            f"SESSION COST SUMMARY  (model: {self.model})",
            "=" * 64,
            f"{'#':>2}  {'label':<22} {'in':>8} {'out':>7} {'$':>9}  {'sec':>5}",
        ]
        for i, c in enumerate(self.calls, start=1):
            in_total = c.input_tokens + c.cache_read_tokens + c.cache_write_tokens
            lines.append(
                f"{i:>2}  {c.label[:22]:<22} {in_total:>8} {c.output_tokens:>7} "
                f"${c.usd:>8.4f}  {c.latency_s:>5.1f}"
            )
        lines.append("-" * 64)
        lines.append(
            f"    {'TOTAL':<22} {self.total_input_tokens:>8} {self.total_output_tokens:>7} "
            f"${self.total_usd:>8.4f}  {self.max_latency_s:>5.1f} (max)"
        )
        lines.append("=" * 64)
        return "\n".join(lines)
