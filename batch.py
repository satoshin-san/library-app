import time
import random
import requests
import pandas as pd
import os

import database
import get_images
import scraper

SOURCE_CSV_FILE = "data/book_list.csv"

def get_book_title_author(isbn):
    """書誌情報を取得"""
    clean_isbn = str(isbn).replace('-', '').strip()
    try:
        url = f"https://api.openbd.jp/v1/get?isbn={clean_isbn}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200 and res.json()[0]:
            s = res.json()[0]['summary']
            return s.get('title'), s.get('author')
    except: pass
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{clean_isbn}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200 and "items" in res.json():
            v = res.json()['items'][0]['volumeInfo']
            return v.get('title'), v.get('authors', [''])[0]
    except: pass
    return "タイトル未取得", "著者不明"

def load_isbns_from_csv():
    """CSVからISBNを読み込む"""
    if not os.path.exists(SOURCE_CSV_FILE): return []
    try:
        try: df = pd.read_csv(SOURCE_CSV_FILE, encoding='utf-8')
        except: df = pd.read_csv(SOURCE_CSV_FILE, encoding='cp932')
        if len(df.columns) >= 4:
            l = df.iloc[:, 3].dropna().astype(str).tolist()
            return [''.join(filter(lambda x: x.isdigit() or x.upper()=='X', i)) for i in l if len(i)>9]
    except: pass
    return []

def main():
    database.init_db()
    target_isbns = load_isbns_from_csv()
    if not target_isbns:
        print("❌ 対象ファイルなし/ISBNなし")
        return

    print(f"🚀 {len(target_isbns)}冊の処理を開始...")
    
    for i, isbn in enumerate(target_isbns):
        print(f"\n[{i+1}/{len(target_isbns)}] ISBN: {isbn}")
        
        # A. 基本情報
        title, author = get_book_title_author(isbn)
        
        # B. 画像の取得 (NDL / OpenBD / Google)
        # ※ここではまだ「ダミー画像」にはしません。Noneのままにしておきます。
        image_url = get_images.fetch_book_image(isbn)
        
        # C. Amazon情報の取得 (画像含む)
        amz = scraper.get_amazon_info(isbn)
        
        # --- 画像の最終決定 ---
        # 1. NDL/Googleで見つかっていれば、そのまま採用
        if image_url:
            pass 
        # 2. 見つからなくて、Amazonで画像が取れていれば、Amazon画像を採用！
        elif amz and amz.get("image_url"):
            image_url = amz["image_url"]
            print("  📷 Amazonから画像を確保しました！")
        # 3. それでもなければダミー画像
        else:
            image_url = "https://placehold.jp/150x200.png?text=NO+IMAGE"
            print("  ❌ どこにも画像なし (ダミー設定)")

# D. データの合体 (★ has_kindle と has_audible を追加！)
        book_data = {
            "isbn": isbn,
            "title": title,
            "author": author,
            "image_url": image_url,
            "amazon_url": amz["amazon_url"] if amz else f"https://www.amazon.co.jp/dp/{isbn}",
            "has_kindle": amz["has_kindle"] if amz else False,           # ← 追加
            "is_unlimited": amz["is_unlimited"] if amz else False,
            "is_prime_reading": amz["is_prime_reading"] if amz else False,
            "has_audible": amz["has_audible"] if amz else False,         # ← 追加
            "is_audible": amz["is_audible"] if amz else False
        }
                
        if amz: print("  ✅ Amazon情報取得")
        database.upsert_book(book_data)

        if i < len(target_isbns) - 1:
            time.sleep(random.uniform(10, 18))

    print("\n🎉 完了！")

if __name__ == "__main__":
    main()