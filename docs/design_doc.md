# 📘 My Library App プロジェクト設計書 (v2.0)

**作成日:** 2024/XX/XX
**開発者:** しんちゃん
**メンター:** Gemini

---

# 📑 1. 要件定義書 (Requirements Definition)

## 1.1 プロジェクト概要
* **Mission:** 自分専用の「最強の読書管理＆図書館検索アプリ」を開発する。
* **Vision:**
    * 文字の羅列ではなく、**書影（表紙画像）** を中心とした直感的な本棚を作る。
    * **Googleスプレッドシート** をデータベースとして活用し、データを永続的に管理する。
    * 最寄りの図書館の貸出状況をリアルタイムで把握し、読書ライフを加速させる。

## 1.2 ターゲットユーザー & 特性
* **ユーザー:** しんちゃん（および、視覚優位な学習スタイルを持つユーザー）
* **Pain (課題):**
    * 密集したテキスト情報（CSVやExcelの行・列）を読むのが苦痛。
    * 既存の図書館検索は「文字」ばかりで、直感的に本を選べない。
* **Gain (理想):**
    * パッと見て「これ読みたい！」と直感で選べる画像中心のUI。
    * 難しい操作不要で、自動的に情報が整理整頓される体験。

## 1.3 機能要件 (Functional Requirements)

### 🌳 Must (優先度：高 / 幹)
1.  **ビジュアル本棚 (Gallery View)**
    * 書籍を「表紙画像」付きのカード形式でグリッド表示する。
    * 画像がない場合は、代替画像（No Image）を表示する。
2.  **ハイブリッド画像取得 (Image Fetching)**
    * **Step 1:** 高速な `OpenBD API` で画像取得を試みる。
    * **Step 2:** 取得できない場合のみ、`Amazonスクレイピング` を実行する。
    * **保存:** 画像自体は保存せず、画像の「URL」のみをデータベースに記録する。
3.  **図書館蔵書検索 (Library Search)**
    * `Calil API` を使用し、ユーザーが設定した図書館の蔵書状況を表示する。
    * ステータス例：「貸出可」「貸出中」「蔵書なし」
4.  **Amazon情報連携**
    * `Amazonスクレイピング` により、以下の情報を取得・表示する。
        * Kindle Unlimited 対象か
        * Audible 対象か
        * Prime Reading 対象か
    * クリックでAmazon商品ページへ遷移可能にする。
5.  **データ永続化 (Google Sheets DB)**
    * アプリ上のデータ（書籍リスト、ユーザー設定）は全て **Googleスプレッドシート** に保存する。

### 🌿 Should (優先度：中 / 枝)
1.  **タグ・カテゴリ絞り込み**
    * 「お金の教養」「ライティング」などのタグで本棚をフィルタリングする。
2.  **新規書籍追加**
    * ISBNを入力することで、新しい本をリストに追加できる機能。
3.  **データ更新ボタン**
    * 貸出状況やAmazon情報を、任意のタイミングで最新化する機能。

### 🍂 Won't (優先度：低 / 葉)
* 読書感想のSNSシェア機能（今回は自分用アプリに特化）。
* 複雑なユーザー認証システム（簡易的なID管理で十分）。

---

# 📐 2. 基本設計書 (Basic Design)

## 2.1 システムアーキテクチャ

Python (Streamlit) をフロントエンドとし、Google Sheets をバックエンド（DB）とする構成。

```mermaid
graph TD
    User((👨 ユーザー)) -->|閲覧/操作| App[📱 Streamlit App]
    
    subgraph "Application Layer (Python)"
        App -->|DB読み書き| DB[🏦 database.py]
        App -->|画像URL取得| Img[📸 get_images.py]
        App -->|詳細情報収集| Scraper[🕵️ scraper.py]
        App -->|蔵書確認| Calil[🏛️ Calil API]
    end
    
    subgraph "Data Layer"
        DB <-->|API接続| GSheet[(📊 Google Sheets)]
        Img -->|Request| OpenBD[📚 OpenBD API]
        Scraper -->|Scraping| Amazon[🛒 Amazon Site]
    end