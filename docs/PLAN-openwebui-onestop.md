# 計画書: Open WebUI × Hermes Agent ワンストップ環境

> ゴール: **`docker compose up -d` するだけ**で「Open WebUI(GUI) → Hermes Agent → Ollama」の
> 要件定義環境が**完全ローカル**で立ち上がる。最終的に **Windows向けワンストップ `.sh`**
> （nvidia-container-toolkit 自動導入まで）で誰でも簡単に構築できるようにする。段階的に進める。
> 最終更新: 2026-07-09

---

## 構成（確定）

```
Browser → Open WebUI(:3000) → Hermes Agent(gateway :8642, OpenAI互換) → Ollama(:11434) → LLM(gemma4:12b-it-qat)
```
- 対話は **Ollama直結ではなく Hermes 経由**（Hermesのエージェント機能=スキル/記憶を要件定義で使うため）。
- Hermes の接続先LLMはローカルOllama → **完全ローカル維持**。

### 裏取りした重要仕様（公式 + deepwiki, 2026-07-09）
- Hermes gateway 起動: `command: ["gateway", "run"]`（ENTRYPOINT=hermes → `hermes gateway run`）
- **APIサーバ設定は config.yaml 非対応＝環境変数のみ**: `API_SERVER_ENABLED` / `API_SERVER_KEY` / `API_SERVER_HOST` / `API_SERVER_PORT`（既定8642）
- 他コンテナから届かせるには `API_SERVER_HOST=0.0.0.0`
- Hermes のデータ/設定 dir = **`/opt/data`**（`./hermes-config` マウントで正しい）
- Open WebUI 側: `OPENAI_API_BASE_URL=http://hermes:8642/v1`（**/v1必須**）＋ `OPENAI_API_KEY`（Hermesと一致）＋ `ENABLE_OLLAMA_API=false`
- OpenAI互換EP: `/v1/chat/completions`, `/v1/models`, ヘルス `/health`

---

## 全体ステップ

| Step | 内容 | 状態 |
|---|---|---|
| **1** | **compose に open-webui と hermes(gateway) を配線。GUIから Hermes経由で対話できるようにする** | 🟡 **今回（配線まで）** |
| 2 | Hermes に grill スキル/システムプロンプトを載せ、要件定義対話を検証 | ⬜ |
| 3 | 初回モデル pull 自動化・起動順の安定化（`compose up` だけで確実に整う） | ⬜ |
| 4 | 完全ローカル強化（offline化・テレメトリ無効・APIキー適正化） | ⬜ |
| 5 | Windows向けワンストップ `.sh`（前提チェック → nvidia-container-toolkit 導入 → up → ブラウザ起動） | ⬜ |
| 6 | （後回し）Obsidian記憶層 / grillスキル本格カスタム | ⬜ |

---

## Step 1 詳細（今回＝compose配線まで。**起動確認はユーザー環境**）

### 変更点（`compose.yaml`）
- **hermes**: 対話TUI常駐 → **gatewayサーバ**化。`command: ["gateway","run"]` + 環境変数でAPIサーバ有効化
  （`API_SERVER_ENABLED=true` / `API_SERVER_HOST=0.0.0.0` / `API_SERVER_PORT=8642` / `API_SERVER_KEY=${HERMES_API_KEY:-change-me-local-key}`）
- **open-webui**: Ollama直結 → **Hermesフロント**化
  （`OPENAI_API_BASE_URL=http://hermes:8642/v1` / `OPENAI_API_KEY=${HERMES_API_KEY:-...}` / `ENABLE_OLLAMA_API=false`）
- **ollama**: 誤字 `OLLAMA_NUM_PAEALLEL` → `OLLAMA_NUM_PARALLEL` を修正

### APIキー
- ローカル検証は既定値 `change-me-local-key` で両サービス一致（localhost限定なので当面可）。
- 公開・恒久運用時は `openssl rand -hex 32` で生成し、環境変数 `HERMES_API_KEY` を設定（compose の `${HERMES_API_KEY:-...}` が両サービスに同じ値を注入）。

### 起動・確認手順（**あなたの docker 環境で実行**。`!` 付けでこのセッションに貼付可）
```bash
cd <repo>/ollama-hermes-docker
# 必要なら鍵を設定（未設定なら既定 change-me-local-key で動く）
# export HERMES_API_KEY=$(openssl rand -hex 32)

docker compose up -d                       # ollama + hermes + open-webui
docker compose ps

# Hermes gateway 疎通
docker compose exec hermes curl -s http://localhost:8642/health
# モデル一覧（Bearer は HERMES_API_KEY。既定なら change-me-local-key）
docker compose exec hermes curl -s -H "Authorization: Bearer change-me-local-key" http://localhost:8642/v1/models

docker compose logs -f open-webui
```
ブラウザ:
- **Windows のブラウザ**で `http://localhost:3000`（WSL2 の localhost 転送で届く）
- 届かなければ WSL で `hostname -I` → `http://<出たIP>:3000`

初回: ローカルにアカウント作成（外部送信なし）→ モデル選択に **Hermes経由のモデル**が出て、チャットが返れば成立。

### 受入基準（Step 1 完了条件）
- [ ] `docker compose up -d` で 3サービス（ollama / hermes / open-webui）が Up。
- [ ] `http://localhost:8642/health` がOK、`/v1/models` がモデルを返す。
- [ ] ブラウザで Open WebUI が開き、**Hermes経由**でチャット応答が返る（= 完全ローカルで対話成立）。

### トラブルシュート
| 症状 | 対処 |
|---|---|
| GUIが開けない | Docker Desktop の WSL integration が**このdistroで有効**か確認 / `hostname -I` のIPで `http://<IP>:3000` |
| モデルが出ない / 401 | Open WebUI の `OPENAI_API_KEY` と Hermes の `API_SERVER_KEY` が**一致**しているか |
| 502 / 接続不可 | Hermes が `API_SERVER_HOST=0.0.0.0` で待受けているか、URLが `http://hermes:8642/v1`（**/v1**）か |
| Hermes 起動失敗 | `docker compose logs hermes`。`config.yaml` の model / base_url(`http://ollama:11434/v1`) と 64k ctx を確認 |
| モデル未DL | `docker compose exec ollama ollama pull gemma4:12b-it-qat` |

---

## 以降のStep（概要・今回は未実施）

### Step 2: Hermes に grill を載せる
- `hermes-config/skills/` に **grill スキル（SKILL.md）**を配置、または Open WebUI のモデルプリセットにgrillシステムプロンプトを設定。
- 中核ロジック（`grilling` 由来）: 1問ずつ／事実は自分で調べ決定はユーザーに委ねる／各問に推奨解／合意まで着手しない。
- 出力ゴール = 引継ぎ書.md（`DESIGN-AND-STATUS.md` §5.4 のテンプレ）。
- ※ `hermes-config/skills/` を実際に読むか（configの `skills.external_dirs` 等）はここで検証。

### Step 3: 「compose up だけ」への安定化
- 初回モデル pull の自動化（entrypoint or `make` ターゲット）。
- 起動順・ヘルスチェック（open-webui は hermes 起動後に接続できるよう `depends_on` + リトライ）。

### Step 4: 完全ローカル強化
- `OFFLINE_MODE=true` / `HF_HUB_OFFLINE=1`（※先に埋め込みモデルを取得してから）。
- APIキーを既定値 `change-me-local-key` から脱却（**自動生成は Step 5 の `.sh` が `.env` で担う**。それまでの手動運用は `export HERMES_API_KEY=$(openssl rand -hex 32)`）。

### Step 5: Windows向けワンストップ `.sh`
**狙い**: GitHub からリポジトリを **clone → `.sh` を起動するだけ**で、初学者ユーザーが環境構築を完了できる。

`.sh` が担う処理（順序）:
1. **前提チェック**: WSL2 / Docker / NVIDIA ドライバの有無を確認。
2. **nvidia-container-toolkit 自動導入**（未導入時のみ）→ Docker 再起動。
3. **APIキーを自動生成**（`.env` が無ければ作る＝**冪等**。既存の鍵は上書きしない）:
   ```bash
   [ -f .env ] || echo "HERMES_API_KEY=$(openssl rand -hex 32)" > .env
   ```
   → `compose.yaml` の `${HERMES_API_KEY:-...}` が `.env` の値を拾い、hermes と open-webui に**同じ鍵**が入る（キー一致は必須）。
4. **初回モデル pull**（未取得時のみ）: `docker compose up -d ollama` → `docker compose exec ollama ollama pull gemma4:12b-it-qat`。
5. **起動**: `docker compose up -d`（ollama / hermes / open-webui）。
6. **疎通待ち → ブラウザ起動**: hermes `/health` が通るまで待ち、既定ブラウザで `http://localhost:3000` を開く。

補足:
- `.env` は `.gitignore` に含める（鍵をコミットしない）。`.gitignore` の現状は要確認・要追記。
- 既存の `wsl-docker-gpu-setup.md` の手順を、この `.sh` に自動化して取り込む形。
- 冪等性: 2回目以降の起動でも鍵・モデル・データを作り直さない（`[ -f .env ]` / `ollama list` チェック / named volume 永続化）。

### Step 6: 後回し
- Obsidian記憶層（MCP、方式A/B/C）、grillスキルの本格カスタム。
