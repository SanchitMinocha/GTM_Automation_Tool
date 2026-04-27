"""
Unified async LLM completion — Anthropic Claude, Groq Cloud, or Google Gemini.

Usage:
    text = await chat_complete(prompt, provider="anthropic", max_tokens=600, fast=True)

provider:  "anthropic" | "groq" | "gemini"
fast=True: cheap/quick model (pain point enrichment, Haiku / llama-3.1-8b / Flash)
fast=False: quality model   (outreach copy, Sonnet / llama-3.3-70b / Pro)
"""
from __future__ import annotations
import os
import httpx

_ANTHROPIC_FAST_MODEL    = "claude-haiku-4-5-20251001"
_ANTHROPIC_QUALITY_MODEL = "claude-sonnet-4-6"
_GROQ_FAST_MODEL         = "llama-3.1-8b-instant"
_GROQ_QUALITY_MODEL      = "llama-3.3-70b-versatile"
_GEMINI_FAST_MODEL       = "gemini-2.0-flash"
_GEMINI_QUALITY_MODEL    = "gemini-2.5-pro-preview-05-06"


async def chat_complete(
    prompt: str,
    provider: str = "anthropic",
    max_tokens: int = 600,
    fast: bool = False,
) -> str:
    """Run a single-turn completion. Returns the raw text string."""
    if provider == "groq":
        return await _groq(prompt, max_tokens, fast)
    if provider == "gemini":
        return await _gemini(prompt, max_tokens, fast)
    return await _anthropic(prompt, max_tokens, fast)


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

async def _anthropic(prompt: str, max_tokens: int, fast: bool) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed — run: pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or "your_" in api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured in .env")

    model = _ANTHROPIC_FAST_MODEL if fast else _ANTHROPIC_QUALITY_MODEL
    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Groq (OpenAI-compatible REST — no extra package needed)
# ---------------------------------------------------------------------------

async def _groq(prompt: str, max_tokens: int, fast: bool) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or "your_" in api_key:
        raise RuntimeError("GROQ_API_KEY not configured in .env")

    model = _GROQ_FAST_MODEL if fast else _GROQ_QUALITY_MODEL
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            },
        )
        if r.status_code != 200:
            raise RuntimeError(f"Groq API {r.status_code}: {r.text[:200]}")
        return r.json()["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------

async def _gemini(prompt: str, max_tokens: int, fast: bool) -> str:
    try:
        from google import genai
    except ImportError:
        raise RuntimeError("google-genai package not installed — run: pip install google-genai")

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or "your_" in api_key:
        raise RuntimeError("GEMINI_API_KEY not configured in .env")

    model = _GEMINI_FAST_MODEL if fast else _GEMINI_QUALITY_MODEL
    client = genai.Client(api_key=api_key)
    response = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(max_output_tokens=max_tokens),
    )
    return response.text.strip()
