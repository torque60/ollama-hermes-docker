# 要件定義サポートAI — 設計と現在地

> 複数セッションで分散していた設計判断・調査結果を1か所に集約したもの。
> 最終更新: 2026-07-09

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

## 3. アーキテクチャ（確定）

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
| Open WebUI（対話フロント） | 🟡 **今回composeに追加**（起動確認はユーザー） | `compose.yaml` |
| grillスキル移植元 | ✅ 取得済（未移植） | `grill-me-skill/.agents/skills/` |
| grillスキルの完全ローカル化（システムプロンプト or Hermesスキル） | ⬜ 未着手 | - |
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

---

## 8. 未解決の論点（フォーク）
- ~~Hermes を使うか~~ → **決定: 使う**（Open WebUI のフロント越しに Hermes gateway。§2）。
- grill を「Hermes のスキル(SKILL.md)」で実装するか、「Open WebUI のモデルプリセット(システムプロンプト)」で実装するか（Step2で検証）。
- ~~`hermes-config/skills/` を読むか~~ → **解決: `/opt/data/skills/`（= ホスト `./hermes-config/skills/`）に置けば永続＆読込。マウント1本で config/skill/memory 全部カバー**。
- 記憶層の実装（§5.5 の A/B/C）。まずは Hermes 組込みメモリで足りるか。
- 中核モデルの最終確定（gemma4:12b-it-qat で進行中）。

---

## 9. 次の一手（ロードマップ）
段階計画は `docs/PLAN-openwebui-onestop.md` を参照。要点:
1. **（今回）** Open WebUI を compose に追加し、ブラウザGUIを開けるようにする。
2. Open WebUI 上で「要件定義用モデル（grillシステムプロンプト）」を設定し、完全ローカル対話を検証。
3. `compose up` だけで整う形に整理（Hermesの `profiles` 化、初回モデルpullの自動化）。
4. 完全ローカル強化（offline化・テレメトリ無効・埋め込みモデル同梱）。
5. Windows向けワンストップ `.sh`（nvidia-container-toolkit 自動導入まで）。
6. （後回し）Obsidian記憶層 / grillスキルの本格カスタム。
