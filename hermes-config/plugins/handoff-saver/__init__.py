"""handoff-saver: 引継ぎ書を /vault に確定保存する Hermes プラグイン。

背景（重要）:
  応答本文をフックで横取りする案は Hermes では不可能。
  - shell フックは envelope のみで応答本文を受け取れない。
  - plugin の post_llm_call / pre_llm_call は VALID_HOOKS に載るだけで
    本体が一度も呼ばない未実装バグ（NousResearch/hermes-agent #2817, closed:not-planned）。
  確実に発火する足場は「ツール呼び出し」だけ。そこで本体に書かせるのをやめ、
  専用ツール save_handoff を1つ生やす。モデルの仕事は「最後にこれを1回呼ぶ」だけで、
  保存パスの決定もファイル書込も全部このコード側でやる（= code for structure）。

小型ローカルモデル(12B)でも、汎用ファイルツールでパスを組ませる（失敗した）のではなく、
project_name と markdown を渡させるだけなので、パス誤り・書込失敗は原理的に起きない。
"""

import json
import re
from pathlib import Path

VAULT_ROOT = Path("/vault/torishirabe")
LOG = Path("/opt/data/plugins/handoff-saver/plugin.log")

# project_name 未指定時のフォールバック用。「# 引継ぎ書: <名>」から名前を拾う。
TITLE_RE = re.compile(r"^#\s*引継ぎ書\s*[:：]\s*(?P<name>.+?)\s*$", re.MULTILINE)

SAVE_SCHEMA = {
    "name": "save_handoff",
    "description": (
        "要件定義の引継ぎ書(Markdown)を確定保存する。全項目が固まったら最後に1回だけ呼ぶ。"
        "project_name にプロジェクト名、markdown に引継ぎ書の全文を渡すと、"
        "/vault/torishirabe/<project_name>/引継ぎ書.md に保存する。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "project_name": {
                "type": "string",
                "description": "プロジェクト名。保存先フォルダ名になる（例: ポモドーロタイマー）。",
            },
            "markdown": {
                "type": "string",
                "description": "引継ぎ書の全文(Markdown)。見出し8項目を含む完成版を丸ごと渡す。",
            },
        },
        "required": ["project_name", "markdown"],
    },
}


def _log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except Exception:
        pass


def _safe(name: str) -> str:
    """フォルダ名に使える形へ。日本語(かな/カナ/漢字)・英数・空白・一部記号のみ残す。"""
    cleaned = re.sub(r"[^\w\-. 　ぁ-んァ-ヶ一-龠]", "_", name).strip()
    return cleaned or "project"


def handle_save(params, **kwargs):
    """save_handoff ツールの実体。呼ばれれば確実に走る（フックと違い実装済み）。"""
    del kwargs
    try:
        markdown = (params.get("markdown") or "").strip()
        name = (params.get("project_name") or "").strip()

        # project_name が空なら本文の見出しから救済的に拾う
        if not name:
            m = TITLE_RE.search(markdown)
            if m:
                name = m.group("name").strip()

        if not markdown:
            _log(f"[ERR] empty markdown. name={name!r}")
            return json.dumps(
                {"success": False, "error": "markdown が空です。引継ぎ書の全文を渡してください。"},
                ensure_ascii=False,
            )

        out = VAULT_ROOT / _safe(name) / "引継ぎ書.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown.rstrip() + "\n", encoding="utf-8")
        _log(f"[SAVED] {out} ({len(markdown)} chars) name={name!r}")
        return json.dumps({"success": True, "saved": str(out)}, ensure_ascii=False)
    except Exception as e:  # 保存に失敗しても会話は止めない
        _log(f"[ERR] save failed: {e}")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


def register(ctx) -> None:
    ctx.register_tool(
        name="save_handoff",
        toolset="handoff",
        schema=SAVE_SCHEMA,
        handler=handle_save,
        description=SAVE_SCHEMA["description"],
    )
    _log("[REGISTER] save_handoff registered")
