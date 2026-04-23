"""
UserPromptSubmit hook: detect ingestion intent, inject decision guide.
Non-blocking — only injects additionalContext to help Claude decide correctly.
"""
import json
import sys
import re

INGEST_KEYWORDS = [
    "入庫", "ingest", "匯入", "新資料", "load data", "import data",
    "data_ingestion", "寫入資料庫", "insert.*db", "解析.*excel",
    "parse.*xlsx", "讀取.*csv.*入庫",
]

INGEST_PATTERN = re.compile("|".join(INGEST_KEYWORDS), re.IGNORECASE)

GATE_MESSAGE = (
    "[INGEST GATE] 偵測到入庫/匯入意圖。啟動 data_ingestion workflow 前請先判斷：\n"
    "  ≤500行 且格式複雜/活文件 → Leader 直接讀寫 Excel，禁寫解析腳本，不入庫\n"
    "  需 AI 理解後結構化（小量）→ AI 直接讀 → 視需要入庫，禁止先寫腳本\n"
    "  >500行 且需跨表JOIN/多腳本共用 → start data_ingestion\n"
    "  >500行 且格式複雜 → start data_ingestion，但先 AI 讀樣本再生成針對性腳本\n"
    "確認後再執行。"
)


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        sys.exit(0)

    prompt = hook_input.get("prompt", "") or ""

    if INGEST_PATTERN.search(prompt):
        result = {"additionalContext": GATE_MESSAGE}
        print(json.dumps(result))

    sys.exit(0)


if __name__ == "__main__":
    main()
