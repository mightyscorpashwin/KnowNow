"""Prompting Azure OpenAI to write one page in the KnowNow format."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Protocol

from .catalog import Target
from .page_schema import PAGE_SCHEMA

PROMPT_VERSION = "2026-11-02.1"

SYSTEM_PROMPT = """You write study pages for KnowNow, an internal learning app for software
engineers, from freshers to senior staff. Each page lets a reader refresh a topic in
a few minutes.

Rules:
- Use ONLY facts found in the SOURCES provided. If the sources do not cover something,
  leave it out rather than guessing. Never invent service names, limits or prices.
- Write plain, direct English. Short sentences. Define jargon the first time it appears.
- overview: 3-5 short markdown paragraphs; start with what it is and why it matters.
- diagram: a small Mermaid diagram (at most 12 nodes) that shows how the parts relate.
  Use 'flowchart LR' or 'flowchart TD'. Quote labels that contain spaces or symbols.
- keyConcepts: 4-10 terms a reader must know.
- comparison: a table comparing the main options; every row has one cell per column.
- whenToUse: 2-8 options with the situation each fits best.
- pitfalls: 3-8 common mistakes.
- quiz: 3-6 multiple-choice questions, exactly 4 options each, answerIndex is 0-based.
- sources: only URLs from the SOURCES list that you actually used.
"""


@dataclass(frozen=True)
class SourceDoc:
    title: str
    url: str
    text: str


def build_messages(target: Target, sources: list[SourceDoc], feedback: list[str] | None = None) -> list[dict]:
    blocks = []
    for i, s in enumerate(sources, 1):
        blocks.append(f"[{i}] {s.title}\nURL: {s.url}\n---\n{s.text}")
    user = (
        f"Topic: {target.topic_name}\n"
        f"Sub-topic: {target.subtopic_name}\n"
        f"Page: {target.area_name}\n\n"
        f"Write the KnowNow page for '{target.subtopic_name}: {target.area_name}'.\n\n"
        "SOURCES:\n\n" + "\n\n".join(blocks)
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    if feedback:
        messages.append(
            {
                "role": "user",
                "content": "Your previous draft failed these checks. Fix every one and return the full page again:\n- "
                + "\n- ".join(feedback),
            }
        )
    return messages


class ChatClient(Protocol):
    def __call__(self, messages: list[dict]) -> str: ...


def make_azure_openai_client(endpoint: str, deployment: str, api_version: str) -> ChatClient:
    """Chat function backed by Azure OpenAI with Entra ID (managed identity) auth."""
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import AzureOpenAI

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version=api_version,
        max_retries=3,
        timeout=180,
    )

    def chat(messages: list[dict]) -> str:
        response = client.chat.completions.create(
            model=deployment,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "knownow_page", "strict": True, "schema": PAGE_SCHEMA},
            },
            max_completion_tokens=12000,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError(f"Empty model response (finish_reason={response.choices[0].finish_reason})")
        return content

    return chat


def draft_page(chat: Callable[[list[dict]], str], messages: list[dict]) -> dict:
    return json.loads(chat(messages))
