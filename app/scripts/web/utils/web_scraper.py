"""
utils/web_scraper.py — Shared fetch-and-summarize logic for web link endpoints.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

SUMMARY_PROMPT = (
    "You are a teaching assistant summarizing a web page for students in a graduate course. "
    "Read the page content below and write a concise summary of 2-3 paragraphs. "
    "Focus only on the educational concepts, facts, definitions, and processes relevant to the topic. "
    "Ignore navigation menus, advertisements, author bios, and unrelated content. "
    "Write in plain prose — no bullet points, no headings."
)


def fetch_page_text(url: str) -> tuple[str, str, list[str]]:
    """Fetch a URL and return (title, text_for_llm, preview_lines).

    Raises on network or HTTP failure.
    """
    try:
        import requests as _requests
        from bs4 import BeautifulSoup as _BS
    except ImportError as exc:
        raise ImportError(f"Missing dependency: {exc}. Run: pip install requests beautifulsoup4") from exc

    headers = {"User-Agent": "Mozilla/5.0 (compatible; GradeAI-Bot/1.0)"}
    resp = _requests.get(url, headers=headers, timeout=20, allow_redirects=True)
    resp.raise_for_status()
    soup = _BS(resp.text, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else url

    for tag in soup.find_all(["script", "style", "nav", "header", "footer",
                               "aside", "noscript", "button", "form"]):
        tag.decompose()

    tags = soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote",
                           "td", "th", "pre", "code", "dt", "dd"])
    lines = [t.get_text(" ", strip=True) for t in tags if len(t.get_text(" ", strip=True)) > 20]
    text = "\n".join(lines)
    return title, text[:12000], lines[:30]


def summarize_text(title: str, text: str, *, provider: str, model: str, api_key: str,
                   max_tokens: int = 600) -> str:
    """Call the chosen LLM to summarize page text. Returns the summary string."""
    user_msg = f"Page title: {title}\n\nPage content:\n{text}"

    if provider == "openai":
        body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()

    if provider == "gemini":
        url_api = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        body = json.dumps({
            "contents": [{"parts": [{"text": SUMMARY_PROMPT + "\n\n" + user_msg}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
        }).encode()
        req = urllib.request.Request(url_api, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"].strip()

    if provider == "anthropic":
        body = json.dumps({
            "model": model,
            "system": SUMMARY_PROMPT,
            "messages": [{"role": "user", "content": user_msg}],
            "max_tokens": max_tokens,
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())["content"][0]["text"].strip()

    raise ValueError(f"Unknown provider: {provider}")


def resolve_summarizer_api_key(provider: str, model: str) -> tuple[str | None, str]:
    """Return (api_key, resolved_model) for the given provider."""
    import os
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY"), model or "gpt-4o-mini"
    if provider == "gemini":
        return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")), model or "gemini-2.0-flash"
    if provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY"), model or "claude-haiku-4-5"
    return None, model
