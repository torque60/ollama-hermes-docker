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
   対話(/torishirabe-n, /torishirabe)  /opt/data/skills     ローカル完結
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

## 9. 次の一手（ロードマップ・2026-07-10 更新）
> 旧 `docs/PLAN-openwebui-onestop.md` は Open WebUI 前提のため大半が無効（先頭に廃止注記済）。
1. ✅ Hermes CLI/TUI ＋ `/torishirabe-n`・`/torishirabe` を同梱（Open WebUI 廃止）。
2. **（次）** 実機で **/torishirabe-n → `./vault/torishirabe/<名>/` に 決定ログ.md → 引継ぎ書.md を1本通す**（＝7/16ポスターの統合検証1回）。
3. `up`(ollama) ＋ `run`(hermes) の初回導線整理（初回モデルpull自動化、`config.yaml` 既定モデル確認）。
4. 完全ローカル強化（offline化）。
5. Windows向けワンストップ `.sh`（前提チェック → nvidia-container-toolkit 自動導入 → `up -d` → `run --rm -it hermes` 案内）。※APIサーバ不使用なので鍵生成は不要。
6. （後回し）Obsidian記憶層。
