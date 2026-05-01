# 学長オススメ書籍 本の案内所

表紙画像を中心としたビジュアル本棚アプリです。学長おすすめの129冊を、Kindle Unlimited・Audible・Prime Reading の対応状況や図書館の貸出状況とあわせて一覧できます。

**Streamlit Cloud で動作**: https://my-library-app.streamlit.app（デプロイ後に更新）

---

## 主な機能

| 機能 | 説明 |
|------|------|
| ビジュアル本棚 | 表紙画像グリッドで全129冊を一覧 |
| ウィザードナビ | 目的別（ランキング・購入・Audible・電子書籍・図書館・激安・ジャンル）で絞り込み |
| Kindle / Audible バッジ | KU・Prime Reading・Audible 聴き放題を色バッジで表示 |
| 図書館検索 | Calil API でリアルタイムの貸出状況を確認 |
| ウィッシュリスト | 気になる本を最大10冊保存 |
| お気に入り | ハートボタンでブックマーク |

---

## セットアップ

### 必要なもの

- Python 3.9+
- Calil API キー（[無料取得](https://calil.jp/api/dashboard/)）

### インストール

```bash
# リポジトリをクローン
git clone <YOUR_REPO_URL>
cd my_library_app

# 仮想環境
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 依存パッケージ
pip install -r requirements.txt
```

### シークレット設定

`.streamlit/secrets.toml` を作成：

```toml
CALIL_API_KEY = "あなたのAPIキーをここに"
```

> Streamlit Cloud にデプロイする場合は、ダッシュボードの **Settings > Secrets** に同じ内容を貼り付けてください。

### 起動

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` が開きます。

---

## データ更新（書籍情報の再取得）

書籍リスト（`data/book_list.csv`）を更新した後、以下を実行すると Amazon の Kindle/Audible 情報と表紙画像を取得して `data/books.csv` を更新します。

```bash
python batch.py
```

> 1冊あたり約5秒かかります（Amazon へのアクセス制限回避のため）。129冊で約10分。

---

## ファイル構成

```
my_library_app/
├── app.py              # Streamlit メインアプリ
├── batch.py            # 書籍情報一括取得スクリプト
├── scraper.py          # Amazon スクレイピング
├── get_images.py       # 書影取得（NDL / OpenBD / Google Books）
├── calil.py            # 図書館検索（Calil API）
├── database.py         # CSV 読み書き・ウィッシュリスト管理
├── requirements.txt
├── assets/
│   ├── favicon.ico
│   └── ChatGPT Image 2026年5月1日 10_21_14.png  # ヒーローバナー
├── data/
│   ├── book_list.csv   # 元の ISBN リスト（バッチ入力）
│   ├── books.csv       # メインデータベース（バッチ出力）
│   └── city_code.csv   # 市区町村コード（Calil 用）
└── .streamlit/
    └── secrets.toml    # APIキー（Git管理外）
```

---

## 使用 API・サービス

| サービス | 用途 |
|----------|------|
| [OpenBD](https://openbd.jp/) | タイトル・著者の書誌情報取得 |
| [Google Books API](https://developers.google.com/books) | タイトル・著者のフォールバック |
| [国立国会図書館（NDL）](https://ndlsearch.ndl.go.jp/) | 表紙サムネイル |
| [Amazon.co.jp](https://www.amazon.co.jp/) | Kindle/Audible 対応状況・表紙画像 |
| [Calil API](https://calil.jp/api/) | 図書館の貸出状況リアルタイム検索 |

---

## ライセンス

個人利用目的のプロジェクトです。Amazon スクレイピング部分は利用規約の範囲内で行っています。
