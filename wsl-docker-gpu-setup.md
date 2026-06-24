# WSL2 + Docker で GPU を使う — nvidia-container-toolkit 導入手順

WSL2 上の Docker で GPU を使うための `nvidia-container-toolkit` 導入手順。
Ollama に限らず、GPUを使うすべてのコンテナで共通の前提。

---

## 前提知識：どこに何を入れるか（3層の責務分担）

GPU利用は3つの層に分かれる。**入れる場所を間違えると動かない**ので最初に整理する。

| 層 | 入れるもの | 入れないもの |
|---|---|---|
| ① **Windows** | NVIDIA GPUドライバ（WSL対応版） | — |
| ② **WSLディストロ（Dockerホスト）** | `nvidia-container-toolkit` だけ | ❌ GPUドライバ |
| ③ **コンテナの中** | （CUDAランタイムはイメージ任せ） | ❌ GPUドライバ ❌ toolkit |

- **GPUドライバはWindows側だけ**に入れる。WSL内に入れると競合して壊れる。
- **WSLに入れるのは toolkit だけ**。toolkitは「ホストのGPUをコンテナへ橋渡しするDockerランタイム拡張」なので、ホストに1回入れれば全コンテナで使える。

> このドキュメントは層②（WSL内での toolkit 導入）を扱う。
> 層①（Windows側ドライバ）は NVIDIA公式サイトからWSL対応ドライバを入れておくこと。

---

## 導入手順（WSLディストロ内で実行）

### 1. 前提パッケージ
```bash
sudo apt-get update && sudo apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg2
```

### 2. NVIDIA公式リポジトリを追加
> `nvidia-container-toolkit` は Ubuntu 標準リポジトリに**無い**。
> これを忘れると `E: Unable to locate package nvidia-container-toolkit` になる。

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
&& curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```

### 3. 更新してインストール
```bash
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
```

### 4. Dockerに登録して再起動
```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 5. 動作確認
```bash
docker run --rm --gpus all ubuntu nvidia-smi
```
→ GPU一覧が表示されれば成功。

> `nvidia-smi` は toolkit がホストからコンテナに注入するので、CUDAイメージは不要（軽い `ubuntu` でよい）。これが公式の推奨テスト。
> `could not select device driver` 等が出る場合のみ `--runtime=nvidia` を足す:
> `docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi`

---

## コマンド逐行解説

### 手順1：前提パッケージ

| コマンド / 部品 | 意味 |
|---|---|
| `sudo apt-get update` | aptのパッケージ一覧（インデックス）を最新化する。これをしないと新しいパッケージが見つからない |
| `&&` | 左のコマンドが成功したら右を実行する連結。失敗時は止まる |
| `sudo apt-get install -y` | パッケージをインストール。`-y` は確認プロンプトに自動でYesと答える |
| `--no-install-recommends` | 必須でない「推奨」パッケージを入れない。余計なものを増やさないため |
| `ca-certificates` | HTTPS通信の証明書検証に必要。これが無いと公式サイトに安全に接続できない |
| `curl` | URLからファイルをダウンロードするツール（後の手順で鍵やリストを取得） |
| `gnupg2` | GPG鍵を扱うツール。リポジトリの署名検証に使う |

### 手順2：リポジトリ追加（この手順が一番複雑なので分解）

**前半：GPG鍵の取得と登録**

| コマンド / 部品 | 意味 |
|---|---|
| `curl -fsSL https://nvidia.github.io/.../gpgkey` | NVIDIAの公開鍵(GPGキー)をダウンロード。`-f`失敗時にエラー / `-s`進捗非表示 / `-S`エラーは表示 / `-L`リダイレクト追従 |
| `\| `（パイプ） | 左の出力を右のコマンドの入力に渡す |
| `sudo gpg --dearmor` | テキスト形式の鍵をバイナリ形式に変換する（aptが読める形にする） |
| `-o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg` | 変換した鍵を、aptが信頼鍵を置く場所に保存する |

**後半：aptソースリストの作成**

| コマンド / 部品 | 意味 |
|---|---|
| `curl -s -L https://nvidia.github.io/.../nvidia-container-toolkit.list` | NVIDIAリポジトリの定義（どこからパッケージを取るか）をダウンロード |
| `sed 's#deb https://#deb [signed-by=...] https://#g'` | ダウンロードした定義行に「この鍵で署名検証せよ」という指定(`signed-by`)を差し込む。`sed`は文字列置換ツールで、`#`は区切り文字（URL中の`/`と衝突を避けるため） |
| `sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list` | 加工後の定義を、aptがリポジトリ一覧を読む場所にファイルとして書き込む。`tee`はsudo権限でファイル書き込みするための定番手法 |

> まとめると手順2は「①NVIDIAの鍵を信頼登録 → ②NVIDIAリポジトリをaptに教える」をやっている。

### 手順3：更新とインストール

| コマンド / 部品 | 意味 |
|---|---|
| `sudo apt-get update` | 手順2で追加したNVIDIAリポジトリを含めて、再度パッケージ一覧を読み直す。これで`nvidia-container-toolkit`が見つかるようになる |
| `sudo apt-get install -y nvidia-container-toolkit` | 本体をインストール |

### 手順4：Docker連携

| コマンド / 部品 | 意味 |
|---|---|
| `sudo nvidia-ctk runtime configure --runtime=docker` | Dockerの設定ファイル(`/etc/docker/daemon.json`)を書き換え、GPU用ランタイムを登録する。`nvidia-ctk`はtoolkit付属の設定ツール |
| `sudo systemctl restart docker` | 設定を反映するためDockerを再起動する |

### 手順5：確認

| コマンド / 部品 | 意味 |
|---|---|
| `docker run --rm --gpus all` | コンテナを起動し、`--gpus all`で全GPUをコンテナに割り当てる。`--rm`は終了後に自動削除。toolkitが入っていて初めて有効 |
| `ubuntu` | テスト用の軽量イメージ。`nvidia-smi`はtoolkitがホストから注入するのでCUDAイメージ不要 |
| `nvidia-smi` | コンテナ内でGPU状態を表示するコマンド。一覧が出れば橋渡し成功 |

---

## トラブルシュート

| 症状 | 原因 / 対処 |
|---|---|
| `E: Unable to locate package nvidia-container-toolkit` | 手順2（リポジトリ追加）をやっていない。手順2→手順3の`apt-get update`の順で解決 |
| `systemctl restart docker` が効かない / エラー | **Docker Desktop の WSL integration** を使っている場合は `systemctl` ではなく **Docker Desktop 側を再起動**する。`systemctl`が有効なのはWSL内にDocker Engineを直接入れた構成のみ |
| `docker run --gpus all` で `could not select device driver` | Windows側のWSL対応NVIDIAドライバ未導入、または手順4未実施。Windowsドライバ確認 + 手順4を再実行 |
| `nvidia-smi` がコンテナ内で動かない | 層①（Windowsドライバ）を確認。WSL内に誤ってLinux GPUドライバを入れていないかも確認 |

---

## 参考（公式）

- [NVIDIA — Container Toolkit Installation Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)（導入コマンドの一次ソース）
- [NVIDIA — CUDA on WSL User Guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)（WSL内にLinuxドライバを入れない、の根拠）
- [Microsoft Learn — Enable NVIDIA CUDA on WSL 2](https://learn.microsoft.com/en-us/windows/ai/directml/gpu-cuda-in-wsl)
