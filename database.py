import pandas as pd
import os
from datetime import datetime
import json
import time

DATA_FOLDER = "data"
BOOKS_FILE = os.path.join(DATA_FOLDER, "books.csv")
API_HISTORY_FILE = os.path.join(DATA_FOLDER, "api_history.json")
WISHLIST_FILE = os.path.join(DATA_FOLDER, "wishlist.csv")
WISHLIST_MAX = 10


# ========== 📋 図書館検索リスト (ウィッシュリスト) ==========
def get_wishlist():
    """登録済みISBNリストを返す"""
    if not os.path.exists(WISHLIST_FILE):
        return []
    try:
        df = pd.read_csv(WISHLIST_FILE, dtype={"isbn": str})
        return df["isbn"].dropna().tolist()
    except Exception:
        return []

def add_to_wishlist(isbn):
    """ISBNをリストに追加する。10冊超えたらFalseを返す"""
    current = get_wishlist()
    if isbn in current:
        return True  # すでに登録済み
    if len(current) >= WISHLIST_MAX:
        return False  # 上限超え
    current.append(isbn)
    pd.DataFrame({"isbn": current}).to_csv(WISHLIST_FILE, index=False)
    return True

def remove_from_wishlist(isbn):
    """ISBNをリストから削除する"""
    current = get_wishlist()
    if isbn in current:
        current.remove(isbn)
    pd.DataFrame({"isbn": current}).to_csv(WISHLIST_FILE, index=False)

def is_in_wishlist(isbn):
    """ISBNがリストに含まれるか確認する"""
    return str(isbn) in [str(i) for i in get_wishlist()]
# ============================================================

# ========== 💖 お気に入りリスト (制限なし) ==========
FAVORITE_FILE = os.path.join(DATA_FOLDER, "favorites.csv")

def get_favorites():
    if not os.path.exists(FAVORITE_FILE):
        return []
    try:
        df = pd.read_csv(FAVORITE_FILE, dtype={"isbn": str})
        return df["isbn"].dropna().tolist()
    except Exception:
        return []

def toggle_favorite(isbn):
    current = get_favorites()
    if isbn in current:
        current.remove(isbn)
    else:
        current.append(isbn)
    pd.DataFrame({"isbn": current}).to_csv(FAVORITE_FILE, index=False)

def is_favorite(isbn):
    return str(isbn) in [str(i) for i in get_favorites()]
# ============================================================


# ========== ⏱️ 1時間に6回までメーター機能 ==========
def _get_valid_api_history():
    """過去60分以内の検索履歴だけを残して返す"""
    if not os.path.exists(API_HISTORY_FILE):
        return []
    try:
        with open(API_HISTORY_FILE, "r") as f:
            history = json.load(f)
    except:
        history = []

    current_time = time.time()
    one_hour_ago = current_time - 3600

    # 60分より新しい履歴だけを残す
    valid_history = [t for t in history if t >= one_hour_ago]
    return valid_history

MAX_SEARCHES_PER_HOUR = 100  # カーリルAPI上限 1000冊/時 ÷ 10冊/回

def get_remaining_search_count():
    """残りの検索可能回数（最大100回）を計算する"""
    valid_history = _get_valid_api_history()
    return max(0, MAX_SEARCHES_PER_HOUR - len(valid_history))

def consume_search_count():
    """検索を1回実行した時間を記録する"""
    valid_history = _get_valid_api_history()
    valid_history.append(time.time()) # 今の時間を記録
    
    with open(API_HISTORY_FILE, "w") as f:
        json.dump(valid_history, f)
# ==================================================


def init_db():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    if os.path.exists(BOOKS_FILE):
        try:
            df = pd.read_csv(BOOKS_FILE)
            # 🌟 新しい列がなければ追加する（アップデート機能）
            needs_update = False
            for col in ["is_prime_reading", "has_kindle", "has_audible"]:
                if col not in df.columns:
                    df[col] = False
                    needs_update = True
            
            if needs_update:
                df.to_csv(BOOKS_FILE, index=False)
                print("✅ データベースをアップデートしました（has_kindle等を追加）")
            return
        except Exception as e:
            print(f"⚠️ データベース読み込みエラー: {e}")

    # 🌟 最初から全カラムを作る
    df = pd.DataFrame(columns=[
        "isbn", "title", "author", "image_url", "amazon_url", 
        "has_kindle", "is_unlimited", "is_prime_reading", 
        "has_audible", "is_audible",
        "updated_at"
    ])
    df.to_csv(BOOKS_FILE, index=False)

def get_all_books():
    if os.path.exists(BOOKS_FILE):
        try:
            return pd.read_csv(BOOKS_FILE, dtype={"isbn": str})
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def upsert_book(book_data):
    df = get_all_books()
    
    if df.empty and "isbn" not in df.columns:
         df = pd.DataFrame(columns=[
            "isbn", "title", "author", "image_url", "amazon_url", 
            "has_kindle", "is_unlimited", "is_prime_reading",
            "has_audible", "is_audible", "updated_at"
        ])

    book_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not df.empty and book_data["isbn"] in df["isbn"].values:
        idx = df.index[df["isbn"] == book_data["isbn"]][0]
        for key, value in book_data.items():
            df.at[idx, key] = value
    else:
        new_row = pd.DataFrame([book_data])
        df = pd.concat([df, new_row], ignore_index=True)
        
    df.to_csv(BOOKS_FILE, index=False)