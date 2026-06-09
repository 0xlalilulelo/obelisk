"""The Block Coach agent loop — a single Claude agent over a bare tool-use loop.

Deliberately framework-free (no LangChain): the loop, the tool dispatch, and the
cost accounting are all visible here so the cost model is easy to reason about.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from anthropic import Anthropic
from anthropic.types import Message, MessageParam, ToolParam
from dotenv import load_dotenv

from obelisk_api.agent.block import Block
from obelisk_api.agent.cost_tracker import CostTracker
from obelisk_api.agent.system_prompt import build_system_prompt
from obelisk_api.tools import registry as coach_tools

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192
MAX_TOOL_ITERATIONS = 16


class MissingAPIKeyError(RuntimeError):
    """Raised when ANTHROPIC_API_KEY is not configured."""


def resolve_model() -> str:
    return os.environ.get("OBELISK_MODEL", DEFAULT_MODEL)


def require_client() -> Anthropic:
    """Build the Anthropic client, failing loudly if the key is absent."""
    load_dotenv()
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise MissingAPIKeyError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return Anthropic(api_key=key)


def _block_to_param(content_block: object) -> dict[str, object]:
    """Serialize one response content block into a message-param dict."""
    kind = getattr(content_block, "type", None)
    if kind == "text":
        return {"type": "text", "text": getattr(content_block, "text", "")}
    if kind == "tool_use":
        return {
            "type": "tool_use",
            "id": getattr(content_block, "id", ""),
            "name": getattr(content_block, "name", ""),
            "input": getattr(content_block, "input", {}),
        }
    # Fallback: best-effort dump.
    dump = getattr(content_block, "model_dump", None)
    return dump() if callable(dump) else {"type": "text", "text": str(content_block)}


def _assistant_text(message: Message) -> str:
    parts = [b.text for b in message.content if b.type == "text"]
    return "\n".join(p for p in parts if p).strip()


@dataclass
class BlockCoach:
    """Drives one Block's conversation."""

    block: Block
    client: Anthropic
    system_prompt: str
    tracker: CostTracker
    # Hard USD ceiling for the session. None or <= 0 means no limit. When the
    # running total reaches it, the loop stops *before* the next paid call.
    max_cost_usd: float | None = None

    @classmethod
    def create(cls, block: Block, max_cost_usd: float | None = None) -> BlockCoach:
        return cls(
            block=block,
            client=require_client(),
            system_prompt=build_system_prompt(block.athlete),
            tracker=CostTracker(model=block.model),
            max_cost_usd=max_cost_usd,
        )

    def _over_ceiling(self) -> bool:
        return (
            self.max_cost_usd is not None
            and self.max_cost_usd > 0
            and self.tracker.total_usd >= self.max_cost_usd
        )

    def _ceiling_message(self) -> str:
        return (
            f"[stopped: session cost ${self.tracker.total_usd:.4f} reached the "
            f"${self.max_cost_usd:.2f} ceiling — no further API calls were made. "
            f"Raise the limit with --max-cost to continue.]"
        )

    def _system_param(self) -> list[dict[str, object]]:
        # Cache the (large) system prompt so follow-up turns are cheap.
        return [
            {
                "type": "text",
                "text": self.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def _call_api(self, label: str, tools: list[ToolParam]) -> Message:
        start = time.perf_counter()
        response = self.client.messages.create(
            model=self.block.model,
            max_tokens=MAX_TOKENS,
            system=self._system_param(),  # type: ignore[arg-type]
            tools=tools,
            messages=self._messages_param(),
        )
        latency = time.perf_counter() - start
        usage = response.usage
        self.tracker.record(
            label=label,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            latency_s=latency,
        )
        print(self.tracker.format_last_call())
        return response

    def _messages_param(self) -> list[MessageParam]:
        return [m for m in self.block.messages]  # type: ignore[misc]

    def send(self, user_text: str) -> str:
        """Send a user message; run the tool loop until a final text answer."""
        # Pre-flight: if we're already at the ceiling, don't even record the turn.
        if self._over_ceiling():
            return self._ceiling_message()

        self.block.messages.append({"role": "user", "content": user_text})
        tools = coach_tools.tool_specs()
        final_text = ""

        for i in range(MAX_TOOL_ITERATIONS):
            # Stop before any paid call once the ceiling is reached (e.g. a turn
            # with many tool round-trips crossed it mid-flight).
            if self._over_ceiling():
                final_text = self._ceiling_message()
                print(final_text)
                break
            label = (
                "block-creation" if "draft" in user_text.lower() and i == 0 else f"turn-step-{i}"
            )
            response = self._call_api(label, tools)  # type: ignore[arg-type]

            assistant_content = [_block_to_param(b) for b in response.content]
            self.block.messages.append({"role": "assistant", "content": assistant_content})

            # Always pair every tool_use with a tool_result, regardless of
            # stop_reason. A response truncated at max_tokens can still carry a
            # tool_use block; leaving it unanswered corrupts the message history
            # and the next call 400s. Only stop when there are no tool calls.
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                final_text = _assistant_text(response)
                if response.stop_reason == "max_tokens":
                    final_text += "\n\n[note: response was truncated at max_tokens]"
                break

            tool_results: list[dict[str, object]] = []
            for cb in tool_uses:
                tool_input = cb.input if isinstance(cb.input, dict) else {}
                result = coach_tools.dispatch(self.block, cb.name, tool_input)
                print(f"  [tool] {cb.name} -> {result.splitlines()[0][:100]}")
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": cb.id, "content": result}
                )
            self.block.messages.append({"role": "user", "content": tool_results})
        else:
            final_text = "(stopped: reached max tool iterations)"

        self.block.save()
        return final_text
