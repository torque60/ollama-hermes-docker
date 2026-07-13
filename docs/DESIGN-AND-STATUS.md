# 要件定義サポートAI — 設計と現在地

> 複数セッションで分散していた設計判断・調査結果を1か所に集約したもの。
> 最終更新: 2026-07-10

---

## 0. これは何か（1行）

初学者が「作りたいもの」を**ローカルLLMとの対話(grill=尋問)**で言語化し、その成果物（**引継ぎ書.md**）を**クラウドの高性能AI(Claude Code / Codex)**が受け取って調査・実装する。この「要件定義〜引き継ぎ」までを**完全ローカル**で支援するツール。

---

## 1. プロダクト構想（ビジョン）

### 対象ユーザー
- 何を作りたいかは頭にあるが、要件・制約・技術選定の軸を**言語化できていない初学者**。

### コアの発想
```
[初学者] --対話(grill)--> [ローカルLLM]  ==引継ぎ書.md==>  [クラウドAI] --調査/実装--> [成果物]
          完全ローカル・無料                手動で手渡し        高推論・ライブweb
```
- ローカル側は **「聞き出す(grill)」ことだけに特化**。実装や最新技術調査はやらない。
- 成果物 = **③ハイブリッド引継ぎ書.md**。これがクラウドAIへの入力になる。

### 役割分担（ローカル vs クラウド）

| フェーズ | 担当 | 理由 |
|---|---|---|
| 要件・制約・**選定の軸**を引き出す | **ローカルgrill** | 対話は小型モデルでも実用圏。個人情報が外に出ない |
| 詳細仕様の生成・**最新技術の調査/比較** | **クラウド** | ライブweb必須＋高推論。小型モデルの弱点 |
| 実装・テスト | **クラウド** | 同上 |

### bricks & studs
- **引継ぎ書.md がスタッド（接続契約）**。ローカルのブリックとクラウドのブリックは、この.mdだけで疎結合に接続する。統合コードは書かない（手渡し）。

---

## 2. 【重要】方向転換 (2026-07-09)

当初は **Hermes Agent の CLI/TUI** を対話フロントに想定していたが、以下へ転換:

- **対話フロント: Hermes CLI/TUI → Open WebUI**（ブラウザGUI）
- **要件定義フェーズは完全ローカル**（Open WebUI + Ollama のみで完結）
- **Obsidian記憶層・grillスキルの本格カスタムは後回し**
- **`docker compose up` するだけ**でこの環境が立ち上がることを重視
- 最終的に **Windows向けワンストップ `.sh`**（前提チェック → nvidia-container-toolkit 自動導入 → compose up → ブラウザ起動）で、使う側が簡単に構築できるようにする

### この転換の確定事項（2026-07-09 追補・ユーザー訂正反映）
- **Open WebUI は Hermes Agent のフロントにする**（Ollama直結ではない）。構成: **Browser → Open WebUI → Hermes(gateway:8642, OpenAI互換) → Ollama(11434) → LLM**。
- Hermes は **gateway サーバとして常駐**（`command: ["gateway","run"]`）。APIサーバ設定は **config.yamlでは不可＝環境変数のみ**: `API_SERVER_ENABLED` / `API_SERVER_KEY` / `API_SERVER_HOST=0.0.0.0` / `API_SERVER_PORT=8642`（公式 + deepwiki 裏取り済）。
- Open WebUI 側は OpenAI互換接続: `OPENAI_API_BASE_URL=http://hermes:8642/v1`（**/v1必須**）＋ `OPENAI_API_KEY`（Hermesのkeyと一致）＋ `ENABLE_OLLAMA_API=false`。接続先はローカルHermesなので**完全ローカルは維持**。
- grill は「Hermes のスキル/システムプロンプト」で実装する路線（要件定義フェーズで Hermes を使う）。記憶層・スキル本格カスタムは引き続き後回し。

---

## 2.9 【最重要・再転換】(2026-07-10): Open WebUI 廃止 → CLI/TUI 採用

§2 の「Open WebUI をフロントにする」路線は**撤回**。**実機検証で、OpenWebUI(gateway経由)では Hermes のスキル(`/grill`)が発火しない**ことが判明した。要件定義の核は grill スキルなので、**スキルが確実に発火する Hermes CLI/TUI を対話フロントに採用**し、Open WebUI を構成から外した。

- 新構成: **[初学者] ⇄ Hermes Agent(TUI) → Ollama → LLM**。hermes は常駐させず `docker compose run --rm -it hermes` で**その都度1プロセスだけ**起こす。運用: `up -d`(ollama) → `run --rm -it hermes bash` → `hermes --tui`。--rm でも状態はマウントで永続。
- 【2026-07-10 追補・根拠】keep-alive常駐（gateway idle 等）＋別の tui は hermes が**2プロセス**になり、公式が「session/memory は同時書込み非対応」と警告。→ **単一プロセスの `run --rm` を採用**（公式も "cleaner and supported" と明言）。gateway idle 常駐案は次善（idle gateway は実質書かないが余計な1プロセス）、無command＋tty/stdin_open のidle chat案は非推奨（keep-alive自体が非サポート・EOFで落ちる）。
- 根拠: スキルは `/opt/data/skills/<name>` が `/<name>` スラッシュとして自動登録（公式/deepwiki + 実機確認）。gateway は別経路でスキル非対応。
- 不要化: **Open WebUI サービス／`API_SERVER_*` gateway 設定／`${HERMES_API_KEY}`**（§7 の罠4・5も gateway 前提のため現構成では発生しない）。
- 退路（合意済）: 仮に将来 GUI が要るなら OpenWebUI を戻せるが、**スキル発火が要件のため既定は CLI/TUI**。
- 影響: 「`compose up` だけでGUI」ではなく「`up -d`(ollama) → `run --rm -it hermes bash` → `hermes --tui`」運用。Windows向け `.sh`(§9) はこの新構成に合わせて作る。

## 3. アーキテクチャ（確定・2026-07-10）

```
[初学者] ⇄ Hermes Agent (CLI/TUI) ──> Ollama (:11434) ──GPU──> LLM(gemma等)
   対話(/n-torishirabe, /torishirabe)  /opt/data/skills     ローカル完結
        │
        └── 成果物: 引継ぎ書.md ──(手動で手渡し)──> クラウドAI(Claude Code / Codex)

起動: docker compose up -d                    # ollama だけ常駐
      docker compose run --rm -it hermes bash # hermes を1個起こして入る
      hermes --tui                            # 対話TUI（スキル発火）
```

> ⚠️ 直下の旧図（Open WebUI 3サービス構成・2026-07-09）は**廃止**。参考として残置。

## 3-old. アーキテクチャ（旧・廃止）

```
┌───────────────── docker compose (ollama-hermes-docker) ─────────────────┐
│                                                                          │
│  [Open WebUI] ─http://hermes:8642/v1─> [Hermes Agent] ──> [Ollama] ─GPU  │
│   :8080→host:3000   (OpenAI互換/認証)     gateway:8642      :11434         │
│   ブラウザGUI                              エージェント本体   gemma4:12b等  │
│                                                                          │
│  docker compose up -d  で 3サービス(ollama / hermes / open-webui)が起動    │
└──────────────────────────────────────────────────────────────────────────┘
        │
        └── 成果物: 引継ぎ書.md ──(手動で手渡し)──> クラウドAI(Claude Code / Codex)
```
すべてローカル完結（Hermes の接続先LLMはローカル Ollama）。

---

## 4. 現在地（ステータス）

| 構成要素 | 状態 | 置き場所 |
|---|---|---|
| インフラ compose + Ollama設定 | ✅ 稼働構成あり（pull済） | `ollama-hermes-docker/compose.yaml`, `hermes-config/config.yaml` |
| GPU / flash attn / KVキャッシュq8_0 | ✅ 設定済 | `compose.yaml` の ollama `environment` / `deploy` |
| 対話フロント（Hermes TUI） | ✅ **採用（Open WebUI廃止, 2026-07-10）** | `compose.yaml`（hermes: `profiles:cli`＝`run --rm -it hermes` で1プロセス → `hermes --tui`） |
| grillスキル移植元 | ✅ 取得済（未移植） | `grill-me-skill/.agents/skills/` |
| grillスキル（`/grill`・`/torishirabe`） | ✅ 実装・同梱（CLI/TUIで発火確認済） | `hermes-config/skills/` |
| 引継ぎ書テンプレ | 🟡 設計のみ（下記5.4）。repo成果物化は未 | - |
| 記憶層 (Obsidian Vault × MCP) | ⬜ 方式A/B/C未決定・後回し | - |
| Windows向けワンストップ `.sh` | ⬜ 未着手（最終ゴール） | - |

---

## 5. 構成要素の詳細

### 5.1 インフラ（ollama-hermes-docker の実値）
- `image: ollama/ollama:latest`（公式・Dockerfile不要）、 port `11434:11434`、モデルは `ollama_data` volume に永続化
- `environment`: `OLLAMA_CONTEXT_LENGTH=65536`（64k）, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, ~~`OLLAMA_NUM_PAEALLEL=2`~~（**誤字。§7参照**）
- `deploy` の nvidia GPU 予約ブロックは**有効化済み**（= nvidia-container-toolkit 前提）

### 5.2 ローカルモデル
- **デフォルト = `gemma4:12b-it-qat`**（`config.yaml` の `model.default` および `custom_providers`）
- `custom_providers` に登録済み（全て `context_length: 65536`）: `qwen3.5:4b` / `qwen3.5:9b` / `gemma4:12b` / `gemma4:12b-it-qat`
- **変遷**: 旧設計メモは中核=Qwen3.5-4B想定だったが、現物は12Bがデフォルト。12Bなら grill の質問生成・構造化出力に余裕があり、4B向けの過度な削り込みは不要。
- **【仕様・実機+deepwiki確認】モデル選択は server-side**: OpenWebUIをHermesフロントにする構成では、gatewayの `/v1/models` は**エージェント1件（既定 "hermes-agent"）だけ**返し、OpenAIリクエストの `model` フィールドは**無視**される。裏のLLMは `config.yaml` の `model.default` で固定。→ **OpenWebUI のドロップダウンから裏の Ollama モデルは選べない（仕様。今は gemma4:12b-it-qat 固定で動作）**。変更は `config.yaml model.default` 編集 / `hermes config set model.default <名>` / チャット内 `/model`。複数を選択肢に出すには **プロファイルごとに別 gateway インスタンス（別ポート）→ OpenWebUI に別 Connection として追加**。表示名は `API_SERVER_MODEL_NAME` で改名可（cosmetic）。要件定義ツールとしては1モデル固定で十分。 **※2026-07-10: Open WebUI 廃止により、このモデル選択制約は現構成(CLI/TUI)では無関係（裏のモデルは `config.yaml` の `model.default` で決まる）。**

### 5.3 grillスキル生態系（移植元 = Matt Pocock skills）
| スキル | 役割 |
|---|---|
| `grill-me` | `/grilling` を呼ぶ薄いラッパ |
| `grilling` | **中核**。1問ずつ・容赦なく尋問／事実はコード探索で自己解決／**決定はユーザーに委ねる**／各問に推奨解を添える／合意まで着手しない |
| `grill-with-docs` | grilling + domain-modeling（ADR・用語集を生成しながら） |
| `to-prd` | 会話をPRDへ合成（尋問せず） |
| `handoff` | 会話を引き継ぎ書へ圧縮（次エージェント用） |
- 我々の**引継ぎ書 = handoff + to-prd のハイブリッド**を、初学者向けにテンプレ固定したもの。

### 5.4 引継ぎ書テンプレ（設計・8セクション）
1. ゴール概要 / 2. 機能要件 / 3. 制約・前提 / **4. 技術選定の軸**（無料・OSS優先か / 実行環境 / スキル / 既存資産 / 保守性）/ 5. 決定事項 / 6. 未解決・保留 / 7. 受入基準 / **8. クラウドAIへの申し送り**（「§4の軸で最新技術を調査・比較し推奨構成を提案 → 実装計画」）

### 5.5 記憶層（後回し）
- ユーザーの価値観・作業観を永続化し、毎回の再入力を削減。
- 方針: **Obsidian Vault（=ただの.md群）× MCPサーバ**で読み書き（vendor中立）。Obsidianアプリは実行時依存にしない（app-free MCP）。
- 環境: Hermes=コンテナ内 / Obsidian=WSL直 → **VaultをコンテナにbindマウントしないとMCPから見えない**。
- 実装3択（未決定）: A) 自作FastMCP(~100行, 権限狭い)＝推奨 / B) 公式filesystem流用 / C) 二段構え。
- ※ Hermesには**組込みメモリ**（`~/.hermes/` の USER.md / MEMORY.md）もあり、まずはこれで足りる可能性。

---

## 6. スコープ外・不採用と理由
- **OpenSpec**: Hermes非対応＋spec生成は高推論前提で小型モデルに不向き＋要件定義に実装用SDD成果物は不要 → 後回し。
- **除外**: Amplifier（独立ランタイム化しHermesと競合・early preview）、Kiro（非OSS）、Tessl（GA未達）、BMAD（小型モデルに重い）。

---

## 7. 見つかった不整合・要修正（現物）
1. **`compose.yaml` の環境変数タイポ**: `OLLAMA_NUM_PAEALLEL` → 正しくは `OLLAMA_NUM_PARALLEL`。現状は**変数名が無効なので並列設定が効いていない**（Ollamaは既定値で動作）。→ 今回の編集で修正。
2. **マウント先＆skills（解決済・公式+deepwiki裏取り）**: Hermes の全状態は **`/opt/data`**（`HERMES_HOME=/opt/data` 固定）配下 = `config.yaml` / `.env` / `SOUL.md` / **`skills/`** / `memories/` / `sessions/` / `logs/`。ホスト `~/.hermes` にマップするのが公式例で、現行 `./hermes-config:/opt/data` は**正しく、マウント1本で全部ホスト永続**。**カスタムskillは `./hermes-config/skills/` に置く**（起動ログの `~/.hermes/skills/` は表示ラベルで実体は `/opt/data/skills/`）。旧README本文の `/root/.hermes` は**誤り**（要修正）。
3. **作業シェルに docker が無い**: この Claude Code のシェルには `docker` が入っていない（PATH無・ソケット無）。**`docker compose up` 等の実行はユーザーの docker 環境で行う**。
4. **【ハマり罠・実機で確認】Hermes の鍵 shadowing**: api_server は `API_SERVER_KEY` を **`/opt/data/.env`（=ホスト `./hermes-config/.env`）→ OS環境変数** の順で解決し、初回起動時に env の値が内部 `.env` へ焼き付く。古い値が残ると**OS env(正しい64字)を上書きして起動拒否**（"placeholder or too short"）。対処: `./hermes-config/.env` と `profiles/*/.env` から `API_SERVER_KEY` 行を削除→`--force-recreate`。
5. **【ハマり罠・実機で確認】Open WebUI の PersistentConfig**: `OPENAI_API_KEY`/`OPENAI_API_BASE_URL` は**初回起動時のみ env からDBへ取り込み、以後DB優先**。env を変えても反映されずモデルが出ない（401）。**ただし初回起動時点で env の鍵が正しければ問題にならない**（正しい鍵がそのままDBにシードされるだけ）。今回ハマったのは、試運転で先にプレースホルダを焼き付けた**汚染volume**が原因。→ **方針（確定）: 初回インストールは `.sh` が `openssl rand -hex 32` で鍵を生成してから up するので、既定（`ENABLE_PERSISTENT_CONFIG=true`）のままでOK**（`ENABLE_PERSISTENT_CONFIG=false` は不採用＝2026-07-09 に一度入れて撤回）。汚染された既存DBを直すには: **Admin→Connections で手動更新（今回これで解決）** ／ `RESET_CONFIG_ON_START=true` で一度上書き ／ volume削除（account/履歴も消えるので注意）。

---

## 8. 未解決の論点（フォーク）
- ~~Hermes を使うか~~ → **決定: 使う（CLI/TUIで直接。§2.9）**。
- ~~grill をスキルで実装するか OpenWebUIプリセットか~~ → **決定: Hermesスキル(SKILL.md)。OpenWebUIは廃止（gateway経由でスキル非発火）、CLI/TUIで発火確認。**
- ~~`hermes-config/skills/` を読むか~~ → **解決: `/opt/data/skills/`（= ホスト `./hermes-config/skills/`）に置けば永続＆読込。マウント1本で config/skill/memory 全部カバー**。
- 記憶層の実装（§5.5 の A/B/C）。まずは Hermes 組込みメモリで足りるか。
- 中核モデルの最終確定（gemma4:12b-it-qat で進行中）。

---

## 8.5 信頼性対策: 小型モデルのツール実行を hook で肩代わり (2026-07-13)

実機（gemma 12B）で判明: 小型ローカルモデルは「決まったタイミングで正しいパスにファイル書込ツールを呼ぶ」のが不安定（決定ログを書かない／引継ぎ書がテキストのみ／別フォルダに保存）。加えて **Hermes はスキル本文を invoke したターンにしか注入せず、以降のマルチターンでは system prompt に残さない**（progressive disclosure）ため、長い取り調べの途中で小型モデルがスキルの指示を忘れやすい。

→ 原則「構造はコード・知能はAI」に沿って、**永続化をモデルから剥がしコード側に移す**。ただし
「どこでコードに橋渡しするか（＝どの拡張点が確実に発火するか）」の調査で二転三転したので、確定した結論を記す。

### 拡張点の実測マップ（一次情報で確定 2026-07-13）
| 経路 | 応答本文が取れるか | 実際に発火するか | 採否 |
|---|---|---|---|
| shell フック（config `hooks:`） | ❌ envelope のみ（`hook_event_name/tool_name/tool_input/session_id/cwd/extra`） | ✅（本文なし） | 不可 |
| plugin `post_llm_call` / `pre_llm_call` / `on_session_start`/`end` | ⭕（設計上 `assistant_response`） | **❌ 本体未実装で一度も呼ばれない** | **不可** |
| plugin `pre_tool_call` / `post_tool_call` | ⭕ | ✅ | 発火する唯一の足場 |
| **plugin カスタムツール（`ctx.register_tool`）** | — | ✅ 呼ばれれば確実に実行 | **採用** |

- **plugin の LLM 系フックは死んでいる**: `pre_llm_call/post_llm_call/on_session_start/on_session_end` は `VALID_HOOKS` に載るだけで `run_agent.py` に `invoke_hook()` が無い＝**未実装バグ**。[NousResearch/hermes-agent #2817](https://github.com/NousResearch/hermes-agent/issues/2817)（closed: not planned）。実機でも「プラグインは enabled なのに plugin.log すら出ない」で症状一致。
- **shell フックは応答本文を受け取れない**（stdin は封筒のみ。公式docs + 実測で確認）。
- 教訓: deepwiki / サブエージェントの二次情報は今回いずれも誤り。**一次情報（公式docs 原文・GitHub issue）で裏取り**して初めて確定した。

### 確定した設計: `save_handoff` カスタムツール
フックで応答本文を横取りする案は全滅。確実に走るのは「ツール呼び出し」だけなので、**本体に汎用ファイルツールでパスを組ませる（＝実機で失敗した）のをやめ、専用ツールを1つ生やす**:
- **プラグイン** `hermes-config/plugins/handoff-saver/` が `ctx.register_tool` で **`save_handoff(project_name, markdown)`** を登録。ハンドラが `/vault/torishirabe/<project_name>/引継ぎ書.md` に**決定論的に保存**（パス決定・書込は全部コード）。有効化は `config.yaml` の `plugins.enabled: [handoff-saver]`。
- **モデルの仕事は「最後に `save_handoff` を1回呼ぶ」だけ**。パス構築を委ねないので、以前の *別フォルダに保存* 失敗は原理的に消える。残る不確実性は「ツールを1回呼ぶか」のみ（編集デモなら再試行可、キットにはフォールバック明記）。
- **未採用の候補**: 12B がツール呼び出しすら忘れる場合に備え、`post_tool_call`（発火する）で確認ログを取る／`pre_tool_call` で誘導する等。まず素の `save_handoff` で実機検証してから判断。
- これはポスターの「失敗と学び」に直結（ローカル小型モデルのツール実行の限界＝“書かせずに呼ばせる／橋渡しはコード”という回避策）。

### 実機結果と最終方針（2026-07-13 追記）
- **save_handoff ツールも実機で不発**: プラグインは `[REGISTER]` まで到達するが `save_handoff` が一度も呼ばれず `[SAVED]` が出ない。`platform_toolsets.cli` / `known_plugin_toolsets.cli` に `handoff` を追加してもモデルが呼ばない（toolset 露出の不確実性＋Hermes が起動時に config を書き戻す性質）。→ **フック系・ツール系＝モデル/フレームワーク依存の経路は全滅**。
- **確実に動くのは state.db 直読み**（`scripts/save_handoff.py`）: Hermes が `/opt/data/state.db`(SQLite) に永続化した会話から「# 引継ぎ書:」を決定論的に抽出。モデル挙動に非依存で確実。**ただし Hermes 固有**（他エージェントでは使えない）。

### 訂正: hooks は「全滅」ではなかった — `transform_llm_output` が正解（2026-07-13）
公式docs 原文の再精読で判明。応答本文を受け取れる**実装済みのプラグイン経路が2つ**あった。当初 `post_llm_call`（唯一の未実装フック #2817）を掴んだのが敗因で、「hooks 全滅」は誤りだった。
- **`transform_llm_output`（plugin フック）＝採用**: `def cb(response_text, session_id, model, platform, **kwargs) -> str|None`。**`response_text` にアシスタントの最終応答本文**が入る。毎ターン、ツールループ後・配信前に発火。`None` を返せば出力素通し（fire-and-forget 捕捉）。#2817 の未実装リストには**含まれない**（transform 系は truncation/redaction パイプラインで実際に使われる実装済み機能）。→ handoff-saver を `transform_llm_output` 登録に変更し、`# 引継ぎ書:` を検知して保存。save_handoff ツール方式と config の toolset 追記は撤去。
- **Memory Provider プラグイン `sync_turn(user_content, assistant_content, *, session_id, messages)`＝高確度フォールバック**: 「各ターン完了後」に呼ばれ **`assistant_content` を受け取る**。docs が test・reference 実装ありと明記＝確実に実装済み。会話観測が本来の用途で相性も最良。transform_llm_output が不発ならこちら。
- shell フックはやはり本文不可（stdin は封筒のみ）。本文が取れるのは plugin の `transform_llm_output` / `post_llm_call`(未実装) / memory `sync_turn` だけ。
- **教訓**: 同じ family の隣のフックのシグネチャまで読まずに詰み扱いした。一次docs は引数まで精読すること。二次情報（deepwiki/サブエージェント）は今回も部分的に誤り。

### 最終決定（2026-07-13）: 自動保存は断念、成果物は「画面上の引継ぎ書ブロック」
上記の手段（shell hook / `post_llm_call` / `save_handoff` ツール / `transform_llm_output` プラグイン / state.db 抽出）を順に試したが、「ローカル小型モデル(gemma 12B)＋Hermes」で確実な自動保存に至らなかった。最後は**プラグインがそもそもロードされず register も走らない**環境事象まで確認（config に `plugins.enabled` はあり、コードも配置済みなのに `plugin.log` が 0 バイト）。締切(7/16)を優先し、**自動保存の実装を打ち切り**、handoff-saver プラグイン・`plugins.enabled`・state.db 抽出スクリプトを撤去した。
- **成果物の受け渡し**: 取り調べの結果、会話に `# 引継ぎ書: <名>` ブロックが出力される。ユーザーがこれをコピーしてクラウドAIへ渡す。動く核（取り調べ→引継ぎ書生成）はこれで完結する。
- これはピッチの「失敗と学び」そのもの: 小型ローカルモデルの自律動作（ツール実行・自己保存）の限界＋フレームワーク拡張点の穴（`post_llm_call` 未実装 #2817、プラグイン非ロード）。**汎用な自動保存は下記「API 層プロキシ」を次フェーズ候補として記録**。

### 汎用化の理想形: 捕捉は「LLM API 層」へ（未実装・設計記録）
問い「色々なエージェントで汎用に使いたい。hooks で会話は読めないのか？」への結論を記録:
- **hooks は汎用捕捉手段にならない**。(a) Hermes ではどのフックでもアシスタント本文を取れない（shell=封筒のみ / plugin LLMフック=未実装 #2817 / tool フック=tool 情報のみ）。(b) そもそも hooks 仕様はフレームワーク毎にバラバラで横断標準が無い（Claude Code の Stop フックは transcript を読めるが Hermes は不可、等）。
- **唯一エージェント非依存の継ぎ目＝全エージェントが叩く OpenAI 互換 API**（`ollama:11434/v1`）。ここに**捕捉プロキシ**を挟めば、Hermes だろうが他のローカルエージェントだろうが base_url を向けるだけで引継ぎ書を回収できる。
  ```
  各エージェント ─base_url→ [capture-proxy] → ollama:11434/v1
                                 └ 応答(JSON/SSE)を覗き「# 引継ぎ書: <名>」検知 → /vault 保存
  ```
- 実装コスト: プロキシ1サービス（自作〜80行 or mitmproxy / LiteLLM proxy）。難所は SSE ストリーム再結合と「最終確定版だけ保存（途中版の乱立回避）」の判定。
- **判断**: 7/16 デモまで時間が無いため未実装。デモは state.db 抽出（実装済・確実）で通し、**汎用化(APIプロキシ)は次フェーズの本命候補として記録**。これ自体がプレゼンの「失敗と学び／今後の展望」に直結。

## 9. 次の一手（ロードマップ・2026-07-10 更新）
> 旧 `docs/PLAN-openwebui-onestop.md` は Open WebUI 前提のため大半が無効（先頭に廃止注記済）。
1. ✅ Hermes CLI/TUI ＋ `/n-torishirabe`・`/torishirabe` を同梱（Open WebUI 廃止）。
2. **（次）** 実機で **/n-torishirabe → `./vault/torishirabe/<名>/` に 決定ログ.md → 引継ぎ書.md を1本通す**（＝7/16ポスターの統合検証1回）。
3. `up`(ollama) ＋ `run`(hermes) の初回導線整理（初回モデルpull自動化、`config.yaml` 既定モデル確認）。
4. 完全ローカル強化（offline化）。
5. Windows向けワンストップ `.sh`（前提チェック → nvidia-container-toolkit 自動導入 → `up -d` → `run --rm -it hermes` 案内）。※APIサーバ不使用なので鍵生成は不要。
6. （後回し）Obsidian記憶層。
