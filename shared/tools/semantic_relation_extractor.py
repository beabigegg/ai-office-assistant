#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PAYLOAD = ROOT / "shared" / "registry" / "semantic_relation_payload.json"
DEFAULT_OUTPUT = ROOT / "shared" / "registry" / "semantic_relation_suggestions.json"
DEFAULT_ENDPOINT = "https://ollama_pjapi.theaken.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-oss:120b"
DEFAULT_USER_AGENT = "ai-office/1.0 (semantic-relation-extractor)"


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def load_payload(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_json_block(text: str):
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


def build_messages(entity: dict) -> list[dict]:
    system_prompt = (
        "You extract semantic capability relations for a governed registry.\n"
        "Return JSON only.\n"
        "Suggest only relations that are plausible from the provided entity summary and current relations.\n"
        "Do not repeat existing relations.\n"
        "Allowed relation types: guided_by, uses, delegates_to, escalates_to, defers_to, prefers.\n"
        "Only suggest targets that already exist in the registry payload.\n"
        "Output shape: {\"suggestions\":[{\"from\":\"...\",\"type\":\"...\",\"to\":\"...\",\"confidence\":\"high|medium|low\",\"reason\":\"...\"}]}"
    )
    user_prompt = json.dumps(entity, ensure_ascii=False, indent=2)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def call_gpt_oss(
    messages: list[dict],
    endpoint: str,
    api_key: str,
    model: str,
    user_agent: str,
    max_tokens: int = 1024,
) -> dict:
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": user_agent,
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            last_err = exc
            if "504" in str(exc) and attempt < 2:
                time.sleep(10)
                continue
            raise
    raise RuntimeError(f"remote request failed: {last_err}")


def cmd_extract(args: argparse.Namespace) -> int:
    load_dotenv()
    payload_path = Path(args.payload) if args.payload else DEFAULT_PAYLOAD
    output_path = (ROOT / args.output).resolve() if args.output else DEFAULT_OUTPUT
    endpoint = os.environ.get("GPT_OSS_ENDPOINT") or DEFAULT_ENDPOINT
    api_key = os.environ.get("GPT_OSS_API_KEY", "")
    model = os.environ.get("GPT_OSS_MODEL") or DEFAULT_MODEL
    user_agent = os.environ.get("GPT_OSS_USER_AGENT") or DEFAULT_USER_AGENT

    if not api_key:
        print("GPT_OSS_API_KEY is required")
        return 1

    payload = load_payload(payload_path)
    if args.limit:
        payload = payload[:args.limit]

    results = {
        "provider": "remote_api_gpt_oss",
        "endpoint": endpoint,
        "model": model,
        "user_agent": user_agent,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "suggestions": [],
        "errors": [],
    }

    for idx, entity in enumerate(payload, start=1):
        try:
            response = call_gpt_oss(
                build_messages(entity),
                endpoint=endpoint,
                api_key=api_key,
                model=model,
                user_agent=user_agent,
                max_tokens=args.max_tokens,
            )
            content = response["choices"][0]["message"]["content"]
            parsed = extract_json_block(content)
            suggestions = parsed.get("suggestions", [])
            for suggestion in suggestions:
                suggestion["source_entity"] = entity["entity_id"]
                results["suggestions"].append(suggestion)
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            results["errors"].append({
                "entity_id": entity.get("entity_id", f"item-{idx}"),
                "error": f"{type(exc).__name__}: {exc}",
            })
        if idx < len(payload):
            time.sleep(args.delay_sec)

    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        shown = output_path.relative_to(ROOT).as_posix()
    except ValueError:
        shown = str(output_path)
    print(f"output: {shown}")
    print(f"suggestions: {len(results['suggestions'])}")
    print(f"errors: {len(results['errors'])}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Remote api-gpt oss semantic relation extraction runner.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="Call remote api-gpt oss and write semantic relation suggestions JSON.")
    p_extract.add_argument("--payload", help="Input payload path. Default: shared/registry/semantic_relation_payload.json")
    p_extract.add_argument("--output", help="Output suggestion path. Default: shared/registry/semantic_relation_suggestions.json")
    p_extract.add_argument("--limit", type=int, help="Only process the first N payload entities.")
    p_extract.add_argument("--delay-sec", type=float, default=3.0, help="Delay between remote calls.")
    p_extract.add_argument("--max-tokens", type=int, default=1024)
    p_extract.set_defaults(func=cmd_extract)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
