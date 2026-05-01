import requests
import time

def fetch_ndl_image(isbn):
    """
    【優先度1位】国立国会図書館サーチ (NDL)
    日本の書籍ならこれが一番高画質！
    """
    url = f"https://ndlsearch.ndl.go.jp/thumbnail/{isbn}.jpg"
    print(f"🏛️ 国立国会図書館で検索中: {url}")
    
    try:
        # 画像が存在するか確認
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return url
    except Exception as e:
        print(f"⚠️ NDLエラー: {e}")
        
    return None

def fetch_openbd_image(isbn):
    """
    【優先度2位】OpenBD
    NDLになかった場合、Googleより先にこちらを聞く。
    技術書などはGoogleより画質が良いことが多い。
    """
    print(f"📸 OpenBDで検索中: {isbn}")
    url = f"https://api.openbd.jp/v1/get?isbn={isbn}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and data[0] is not None:
                return data[0].get('summary', {}).get('cover')
    except Exception as e:
        print(f"⚠️ OpenBDエラー: {e}")
        
    return None

def fetch_google_books_image(isbn):
    """
    【優先度3位】Google Books API
    最後の砦。エラーを防ぐため、無理な高画質化はせず「確実な画像」を返す。
    """
    print(f"🔍 Google Booksで検索中: {isbn}")
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                volume_info = data["items"][0].get("volumeInfo", {})
                image_links = volume_info.get("imageLinks", {})
                thumbnail = image_links.get("thumbnail")
                
                if thumbnail:
                    # 無理な高画質化(zoom=0)はやめて、標準画質(zoom=1)を使う
                    # これで「画像が出ない事故」は防げる！
                    return thumbnail.replace("http://", "https://")
    except Exception as e:
        print(f"⚠️ Google Booksエラー: {e}")
    
    return None

def fetch_book_image(isbn):
    """
    画像を統括して探す編集長関数
    優先順位: NDL -> OpenBD -> Google (安全版)
    """
    clean_isbn = str(isbn).replace('-', '').strip()

    # 1. 国立国会図書館 (NDL)
    image_url = fetch_ndl_image(clean_isbn)
    if image_url:
        print("✅ 国立国会図書館で見つかりました！")
        return image_url

    # 2. OpenBD (順位アップ！)
    image_url = fetch_openbd_image(clean_isbn)
    if image_url:
        print("✅ OpenBDで見つかりました！")
        return image_url

    # 3. Google Books (安全策)
    image_url = fetch_google_books_image(clean_isbn)
    if image_url:
        print("✅ Google Booksで見つかりました！")
        return image_url
        
    print("❌ どこにもありませんでした。")
    return None

# --- テスト実行 ---
if __name__ == "__main__":
    test_isbn = "9784873117584" # ディープラーニングの本
    print("--- テスト開始 ---")
    image_url = fetch_book_image(test_isbn)
    print(f"結果のURL: {image_url}")