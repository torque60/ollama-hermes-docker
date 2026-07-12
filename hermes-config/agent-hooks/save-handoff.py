#!/usr/bin/env python3
"""post_llm_call フック: アシスタント応答が「引継ぎ書」なら /vault に自動保存する。

小型ローカルモデルは「決まったタイミングで正しいパスにファイル書込ツールを呼ぶ」のが
不安定。そこで保存はモデルに頼らず、Hermes の Shell Hook（＝コード）で決定論的に行う。
（原則: 構造はコード・知能はAI）

挙動:
- Hermes が post_llm_call で JSON payload を stdin に渡す。
- アシスタント応答テキストに `# 引継ぎ書: <プロジェクト名>` の見出しがあれば、
  その見出し以降を本体として /vault/torishirabe/<名>/引継ぎ書.md に保存する。
- 見出しが無ければ（通常の質問ターン等）何もしない。
- 標準出力に空JSON `{}` を返す（エージェントの挙動には干渉しない）。
"""

import json
import re
import sys
from pathlib import Path

VAULT_ROOT = Path("/vault/torishirabe")

# 引継ぎ書の見出し（半角/全角コロン両対応）。この行を保存対象の目印にする。
TITLE_RE = re.compile(r"^#\s*引継ぎ書\s*[:：]\s*(?P<name>.+?)\s*$", re.MULTILINE)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print("{}")
        return

    # post_llm_call の最終応答テキスト（キー名の揺れに備えて候補を順に見る）
    text = ""
    if isinstance(payload, dict):
        for key in ("assistant_response", "response", "message", "content", "text"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                text = val
                break

    if not text:
        print("{}")
        return

    m = TITLE_RE.search(text)
    if not m:
        # 引継ぎ書ではない → 何もしない
        print("{}")
        return

    name = m.group("name").strip()
    # フォルダ名に使えない文字を除去（日本語・英数・空白・-._ は許可）
    safe = re.sub(r"[^\w\-. 　ぁ-んァ-ヶ一-龠]", "_", name).strip() or "project"

    # 見出し行以降を引継ぎ書本体として保存
    doc = text[m.start():].rstrip() + "\n"

    out_dir = VAULT_ROOT / safe
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "引継ぎ書.md").write_text(doc, encoding="utf-8")
    except Exception:
        # 保存に失敗しても会話は止めない（引継ぎ書は会話にも残っている）
        pass

    print("{}")


if __name__ == "__main__":
    main()
