"""
TutorForge AI — LLM Provider Abstraction
Supports: Gemini, OpenAI, and a deterministic local fallback.
"""
from __future__ import annotations
import logging
import json
import re
import time
from typing import List, Dict, Any, Optional
from config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
# Standardised error types (never leak internals to frontend)
# ──────────────────────────────────────────

class ProviderError(Exception):
    """Base for all mapped provider errors."""
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)

class AuthenticationError(ProviderError):
    def __init__(self, msg="API authentication failed"):
        super().__init__("AUTHENTICATION_ERROR", msg)

class RateLimitError(ProviderError):
    def __init__(self, msg="Rate limit reached"):
        super().__init__("RATE_LIMIT", msg)

class ModelUnavailableError(ProviderError):
    def __init__(self, msg="Model temporarily unavailable"):
        super().__init__("MODEL_UNAVAILABLE", msg)

class TimeoutError(ProviderError):
    def __init__(self, msg="Request timed out"):
        super().__init__("TIMEOUT", msg)

class ConfigurationError(ProviderError):
    def __init__(self, msg="AI provider not configured"):
        super().__init__("CONFIGURATION_ERROR", msg)


def _map_gemini_error(e: Exception) -> ProviderError:
    """Map raw Gemini SDK exceptions to clean ProviderError types."""
    msg = str(e)
    if "401" in msg or "403" in msg or "API_KEY" in msg or "authentication" in msg.lower():
        return AuthenticationError()
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        return RateLimitError()
    if "503" in msg or "UNAVAILABLE" in msg or "overloaded" in msg.lower():
        return ModelUnavailableError()
    if "deadline" in msg.lower() or "timeout" in msg.lower():
        return TimeoutError()
    if "404" in msg or "NOT_FOUND" in msg:
        return ModelUnavailableError(f"Model not found: {msg[:200]}")
    return ProviderError("UNKNOWN_PROVIDER_ERROR", msg[:200])


class LLMProvider:
    """Abstract base for all LLM providers."""

    def chat(self, messages: List[Dict[str, str]], system_prompt: str = "") -> str:
        raise NotImplementedError

    def is_available(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "unknown"

    @property
    def is_demo(self) -> bool:
        return False


# ──────────────────────────────────────────
# Gemini Provider — with retry + fallback model
# ──────────────────────────────────────────

class GeminiProvider(LLMProvider):
    """
    Google Gemini via google-genai SDK.
    Retries on 503/model-unavailable with exponential backoff.
    Falls back to gemini_fallback_model if primary fails and fallback is configured.
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # seconds, doubled on each retry

    def __init__(self):
        self._client = None
        self._primary_model = settings.gemini_model or "gemini-3.8-flash"
        self._fallback_model = settings.gemini_fallback_model or ""
        self._secondary_fallback = getattr(settings, "gemini_secondary_fallback_model", "")

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    @property
    def provider_name(self) -> str:
        return "Gemini"

    def _call_model(self, model: str, prompt: str) -> str:
        """Single model call — raises ProviderError on failure."""
        client = self._get_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "temperature": 0.4,
                "max_output_tokens": 2048,
            }
        )
        return response.text.strip()

    def chat(self, messages: List[Dict[str, str]], system_prompt: str = "") -> str:
        # Build flat prompt (Gemini doesn't use chat turns in generateContent)
        parts = []
        if system_prompt:
            parts.append(f"SYSTEM: {system_prompt}\n\n")
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            parts.append(f"{role}: {msg['content']}\n")
        parts.append("Assistant:")
        prompt = "".join(parts)

        models_to_try = [m for m in [self._primary_model, self._fallback_model, self._secondary_fallback] if m]
        last_error: Optional[ProviderError] = None

        for model in models_to_try:
            delay = self.RETRY_DELAY
            for attempt in range(self.MAX_RETRIES):
                try:
                    return self._call_model(model, prompt)
                except Exception as e:
                    mapped = _map_gemini_error(e)
                    last_error = mapped
                    if isinstance(mapped, (ModelUnavailableError, TimeoutError)):
                        logger.warning(
                            f"Gemini {mapped.code} on model {model} attempt {attempt+1}/{self.MAX_RETRIES}: {mapped}. "
                            f"Retrying in {delay:.0f}s..."
                        )
                        time.sleep(delay)
                        delay *= 2
                    else:
                        # Authentication / rate-limit / not-found — don't retry on this model
                        logger.error(f"Gemini {mapped.code} on {model}: {mapped}")
                        break
            # If we break or exhaust retries, continue to next model in fallback chain
            logger.warning(f"Model {model} exhausted or failed. Moving to next fallback if available.")

        raise last_error or ModelUnavailableError()

    def is_available(self) -> bool:
        return bool(settings.gemini_api_key)


# ──────────────────────────────────────────
# OpenAI Provider
# ──────────────────────────────────────────

class OpenAIProvider(LLMProvider):
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    def chat(self, messages: List[Dict[str, str]], system_prompt: str = "") -> str:
        try:
            client = self._get_client()
            openai_messages = []
            if system_prompt:
                openai_messages.append({"role": "system", "content": system_prompt})
            openai_messages.extend(messages)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=openai_messages,
                max_tokens=2048,
                temperature=0.4
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def is_available(self) -> bool:
        return bool(settings.openai_api_key)


# ──────────────────────────────────────────
# Local Fallback Provider
# Produces structured, grounded responses for demo mode.
# ──────────────────────────────────────────

class LocalFallbackProvider(LLMProvider):
    """
    Deterministic fallback when no API key is configured.
    Produces realistic demo responses grounded on provided context.
    Clearly labeled as DEMO MODE output — never presented as AI-generated.
    """

    @property
    def provider_name(self) -> str:
        return "Demo"

    @property
    def is_demo(self) -> bool:
        return True

    def chat(self, messages: List[Dict[str, str]], system_prompt: str = "") -> str:
        last_user_msg = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user_msg = m["content"].lower()
                break

        # Extract any context injected in system_prompt
        context_snippet = ""
        if "Context:" in system_prompt:
            ctx_start = system_prompt.index("Context:") + 8
            context_snippet = system_prompt[ctx_start:ctx_start+400].strip()

        # Pattern-match common tutoring intents
        if any(kw in last_user_msg for kw in ["congestion", "tcp"]):
            body = (
                "TCP Congestion Control is a mechanism that regulates the rate at which data is "
                "sent over a network to prevent overloading any network link. It works through "
                "four interrelated algorithms:\n\n"
                "1. **Slow Start** — The sender begins with a small congestion window (cwnd) and "
                "doubles it every round-trip time until a threshold is reached.\n"
                "2. **Congestion Avoidance** — Once the threshold is reached, cwnd grows linearly "
                "rather than exponentially.\n"
                "3. **Fast Retransmit** — When three duplicate ACKs are received, the sender "
                "retransmits the lost segment immediately without waiting for a timeout.\n"
                "4. **Fast Recovery** — After fast retransmit, cwnd is reduced by half and the "
                "connection enters congestion avoidance (not slow start).\n\n"
                "These algorithms allow TCP to efficiently utilise available bandwidth while "
                "backing off when the network signals congestion."
            )
        elif any(kw in last_user_msg for kw in ["udp", "user datagram"]):
            body = (
                "UDP (User Datagram Protocol) is a connectionless transport layer protocol. "
                "Unlike TCP, it provides no guarantees about delivery, ordering, or duplicate "
                "protection. It is lightweight and fast, making it ideal for applications where "
                "low latency matters more than reliability — such as live video streaming, "
                "online gaming, DNS queries, and VoIP.\n\n"
                "Key characteristics:\n"
                "• No connection setup (no handshake)\n"
                "• No acknowledgements or retransmissions\n"
                "• No flow control or congestion control\n"
                "• Small 8-byte header\n"
                "• Application must handle errors if needed"
            )
        elif any(kw in last_user_msg for kw in ["flow control", "sliding window"]):
            body = (
                "Flow Control ensures that a fast sender does not overwhelm a slow receiver. "
                "TCP implements flow control using the **receive window** (rwnd) field in the "
                "TCP header.\n\n"
                "The Sliding Window protocol:\n"
                "• The receiver advertises the size of its available buffer (rwnd)\n"
                "• The sender limits unacknowledged data to min(cwnd, rwnd)\n"
                "• As acknowledgements arrive, the window 'slides' forward\n"
                "• If rwnd = 0, the sender pauses and sends 1-byte probe segments periodically\n\n"
                "This provides end-to-end flow control at the transport layer."
            )
        elif any(kw in last_user_msg for kw in ["quiz", "test", "question"]):
            body = (
                "Sure! Here is a practice question:\n\n"
                "**Question:** A TCP sender receives three duplicate ACKs. What does it do?\n\n"
                "A) Waits for a timeout before retransmitting\n"
                "B) Immediately retransmits the lost segment and halves cwnd\n"
                "C) Closes the connection and reopens it\n"
                "D) Doubles cwnd and continues\n\n"
                "Take your time. When you're ready, let me know your answer!"
            )
        elif any(kw in last_user_msg for kw in ["weak", "gap", "struggling", "help"]):
            body = (
                "Based on your recent performance, here are your areas that need the most attention:\n\n"
                "🔴 **Congestion Control** — 48% mastery. Focus on the four algorithms and how "
                "cwnd changes at each event.\n"
                "🟡 **Sliding Window** — 61% mastery. Review how rwnd interacts with cwnd.\n"
                "🟡 **Flow Control** — 67% mastery. Practice tracing window states step by step.\n\n"
                "I recommend starting with Congestion Control since it is the weakest area. "
                "Shall I explain it step by step?"
            )
        elif context_snippet:
            body = (
                f"Based on your uploaded materials, here is what I found:\n\n"
                f"{context_snippet[:500]}\n\n"
                f"This comes from your course materials. Would you like me to explain any part "
                f"in more detail, give an example, or create a practice question?"
            )
        else:
            body = (
                "I'm your TutorForge AI assistant. I can help you understand concepts from your "
                "uploaded materials, explain topics at different levels, quiz you on what you've "
                "learned, and identify knowledge gaps.\n\n"
                "Try asking me something like:\n"
                "• 'Explain TCP congestion control'\n"
                "• 'Quiz me on sliding window protocol'\n"
                "• 'Where am I weak?'\n"
                "• 'Give me an exam-level explanation of UDP'"
            )

        notice = (
            "\n\n---\n*⚠️ DEMO MODE — No API key configured. "
            "Add GEMINI_API_KEY or OPENAI_API_KEY in .env for full AI responses.*"
        )
        return body + notice

    def is_available(self) -> bool:
        return True


# ──────────────────────────────────────────
# Factory
# ──────────────────────────────────────────

def get_llm_provider() -> LLMProvider:
    """
    Return the best available LLM provider.
    Priority: configured provider → key-detected fallback → demo.
    """
    provider_name = settings.ai_provider.lower()

    if provider_name == "gemini":
        p = GeminiProvider()
        if p.is_available():
            logger.info(f"Using Gemini LLM provider (model: {p._primary_model})")
            return p
    elif provider_name == "openai":
        p = OpenAIProvider()
        if p.is_available():
            logger.info("Using OpenAI LLM provider")
            return p

    # Try any key that is set
    if settings.gemini_api_key:
        logger.info("Falling back to Gemini (key detected)")
        return GeminiProvider()
    if settings.openai_api_key:
        logger.info("Falling back to OpenAI (key detected)")
        return OpenAIProvider()

    logger.info("No AI API key found — using LocalFallbackProvider (DEMO MODE)")
    return LocalFallbackProvider()


# Singleton
llm_provider = get_llm_provider()
