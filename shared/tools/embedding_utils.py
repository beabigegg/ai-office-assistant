#!/usr/bin/env python3
"""embedding_utils.py — 通用 Embedding 工具模組

提供 Ollama 本地 embedding 的通用介面，供 kb_index.py、qar_embed.py 等工具共用。
模型：Qwen3-Embedding-4b（dim=2560），via Ollama localhost:11434。

用法：
    from embedding_utils import get_embedding, cosine_similarity, is_ollama_available
"""
import json
import math
import os
import struct
import urllib.request
import urllib.error
import ssl

OLLAMA_URL = "http://localhost:11434/api/embed"
MODEL = "qwen3-embedding:4b"
_TIMEOUT = float(os.environ.get("OLLAMA_EMBED_TIMEOUT_SEC", "30"))


def is_ollama_available() -> bool:
    """檢查 Ollama 服務是否可用"""
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def get_embedding(text: str, model: str = MODEL) -> list[float]:
    """呼叫 Ollama 取得 embedding 向量

    Args:
        text: 要 embed 的文字
        model: Ollama 模型名稱

    Returns:
        float list (dim=2560 for qwen3-embedding:4b)

    Raises:
        ConnectionError: Ollama 服務不可用
        RuntimeError: API 回傳錯誤
    """
    payload = json.dumps({"model": model, "input": text}).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT, context=ctx) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise ConnectionError(f"Ollama 服務不可用: {e}") from e
    return result["embeddings"][0]


def embedding_to_blob(vec: list[float]) -> bytes:
    """float list → 二進位 blob (little-endian float32)"""
    return struct.pack(f"<{len(vec)}f", *vec)


def blob_to_embedding(blob: bytes) -> list[float]:
    """二進位 blob → float list"""
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """計算兩個向量的 cosine similarity"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
