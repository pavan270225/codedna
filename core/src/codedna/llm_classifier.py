"""LLM-assisted classifier for higher accuracy (opt-in)."""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional

import httpx

from .classifier import Classifier, ClassifierConfig, EditEvent
from .models import Attribution, AttributionLabel


@dataclass
class LLMClassifierConfig:
    """Configuration for LLM classifier."""
    provider: str = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
    api_key_env: str = "CODEDNA_API_KEY"
    max_tokens: int = 100
    temperature: float = 0.1
    timeout_seconds: float = 10.0


class LLMClassifier:
    """LLM-assisted classifier that falls back to heuristic classifier."""

    def __init__(self, config: Optional[LLMClassifierConfig] = None):
        self.config = config or LLMClassifierConfig()
        self.heuristic = Classifier()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def api_key(self) -> Optional[str]:
        return os.environ.get(self.config.api_key_env)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.timeout_seconds)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_prompt(self, event: EditEvent) -> str:
        """Build classification prompt for the LLM."""
        return f"""Classify this code edit as one of: human, ai-generated, ai-modified, ambiguous.

Edit details:
- File: {event.file}
- Lines: {event.start_line}-{event.end_line}
- Inserted: {event.inserted_text[:500]}{"..." if len(event.inserted_text) > 500 else ""}
- Deleted: {event.deleted_text[:500]}{"..." if len(event.deleted_text) > 500 else ""}
- Duration: {event.duration_ms}ms
- Source hint: {event.source_hint or "none"}

Guidelines:
- ai-generated: Bulk code insertions, completions accepted wholesale, superhuman typing speed
- ai-modified: Small targeted changes to existing code (refactors, fixes)
- human: Slow, character-by-character typing with pauses
- ambiguous: Mixed patterns, unclear origin

Respond with ONLY the classification label (human/ai-generated/ai-modified/ambiguous) and a confidence 0.0-1.0, separated by comma.
Example: ai-generated,0.85"""

    async def _call_llm(self, prompt: str) -> tuple[AttributionLabel, float]:
        """Call LLM API and parse response."""
        if self.config.provider == "openai":
            return await self._call_openai(prompt)
        elif self.config.provider == "anthropic":
            return await self._call_anthropic(prompt)
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")

    async def _call_openai(self, prompt: str) -> tuple[AttributionLabel, float]:
        client = await self._get_client()
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            },
        )
        response.raise_for_status()
        data = response.json()
        return self._parse_response(data["choices"][0]["message"]["content"])

    async def _call_anthropic(self, prompt: str) -> tuple[AttributionLabel, float]:
        client = await self._get_client()
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": self.config.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            },
        )
        response.raise_for_status()
        data = response.json()
        return self._parse_response(data["content"][0]["text"])

    def _parse_response(self, text: str) -> tuple[AttributionLabel, float]:
        """Parse LLM response into label and confidence."""
        text = text.strip().lower()
        parts = text.split(",")
        if len(parts) != 2:
            return AttributionLabel.AMBIGUOUS, 0.5

        label_str = parts[0].strip()
        try:
            confidence = float(parts[1].strip())
        except ValueError:
            confidence = 0.5

        label_map = {
            "human": AttributionLabel.HUMAN,
            "ai-generated": AttributionLabel.AI_GENERATED,
            "ai-modified": AttributionLabel.AI_MODIFIED,
            "ambiguous": AttributionLabel.AMBIGUOUS,
        }
        return label_map.get(label_str, AttributionLabel.AMBIGUOUS), confidence

    async def classify(self, event: EditEvent) -> Attribution:
        """Classify an edit event, using LLM if available, otherwise heuristic."""
        if not self.enabled:
            return self.heuristic.classify(event)

        try:
            label, confidence = await self._call_llm(self._build_prompt(event))
            return Attribution(
                file=event.file,
                start_line=event.start_line,
                end_line=event.end_line,
                label=label,
                confidence=confidence,
                source_hint=event.source_hint,
                metadata={
                    "inserted_chars": len(event.inserted_text),
                    "deleted_chars": len(event.deleted_text),
                    "duration_ms": event.duration_ms,
                    "lines_changed": event.end_line - event.start_line + 1,
                    "llm_assisted": True,
                    "provider": self.config.provider,
                    "model": self.config.model,
                },
            )
        except Exception:
            attr = self.heuristic.classify(event)
            attr.metadata["llm_fallback"] = True
            return attr

    async def classify_batch(self, events: list[EditEvent]) -> list[Attribution]:
        """Classify a batch of events."""
        results = []
        for event in events:
            results.append(await self.classify(event))
        return results


async def create_llm_classifier(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key_env: Optional[str] = None,
) -> Optional[LLMClassifier]:
    """Factory to create LLM classifier if configured."""
    config = LLMClassifierConfig()
    if provider:
        config.provider = provider
    if model:
        config.model = model
    if api_key_env:
        config.api_key_env = api_key_env

    classifier = LLMClassifier(config)
    if not classifier.enabled:
        return None
    return classifier