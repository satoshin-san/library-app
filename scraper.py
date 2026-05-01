import requests
from bs4 import BeautifulSoup
import time
import random
import json

def isbn13_to_asin(isbn13):
    """ISBN-13 -> ASIN (ISBN-10) 変換。物理本のページに行くために必要です"""
    isbn13 = str(isbn13).replace('-', '').strip()
    if not isbn13.startswith('978') or len(isbn13) != 13: return isbn13
    body = isbn13[3:-1]
    total = sum(int(d) * (10 - i) for i, d in enumerate(body))
    check = (11 - (total % 11))
    check_char = 'X' if check == 10 else '0' if check == 11 else str(check)
    return body + check_char

def get_random_user_agent():
    """ランダムなUser-Agentを返す"""
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0"
    ]
    return random.choice(user_agents)

def get_soup(url):
    """URLからSoupオブジェクトを作る共通関数"""
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.amazon.co.jp/",
    }
    try:
        time.sleep(random.uniform(4.0, 8.0)) # ブロック回避のため余裕を持って待つ
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print(f"    ⚠️ アクセスエラー: {e}")
    return None

def extract_image_from_soup(soup):
    """【画像抽出係】渡されたページ(soup)から全力で画像を探して返す"""
    if not soup: return None
    img_candidates = ["landingImage", "ebooksImgBlkFront", "imgBlkFront", "books-image-block"]
    for img_id in img_candidates:
        img_tag = soup.find("img", {"id": img_id})
        if img_tag:
            dynamic_data = img_tag.get("data-a-dynamic-image")
            if dynamic_data:
                try:
                    img_dict = json.loads(dynamic_data)
                    if img_dict: return list(img_dict.keys())[0]
                except: pass
            if img_tag.get("src"):
                return img_tag.get("src")
    return None


def get_amazon_info(isbn):
    """メインのスクレイピング部"""
    clean_isbn = str(isbn).replace('-', '').strip()
    
    info = {
        "has_kindle": False,
        "is_unlimited": False,
        "is_prime_reading": False,
        "has_audible": False,
        "is_audible": False,
        "amazon_url": f"https://www.amazon.co.jp/s?k={clean_isbn}",
        "image_url": None
    }

    print(f"  🔍 Amazon検索開始 (ISBN: {clean_isbn})")

    # ==========================================
    # 🟢 ミッション1: 詳細ページへ突入（Kindleか物理本）
    # ==========================================
    search_url_kindle = f"https://www.amazon.co.jp/s?k={clean_isbn}&i=digital-text"
    soup_search = get_soup(search_url_kindle)
    
    target_soup = None
    target_url = None
    
    if soup_search:
        no_result_msg = soup_search.find("h3", class_="a-size-base")
        full_text_search = soup_search.get_text()
        
        # 1. 検索結果が出なかった場合 -> 物理本へ突入
        if (no_result_msg and "結果は見つかりませんでした" in no_result_msg.get_text()) or \
           ("結果は見つかりませんでした" in full_text_search and "すべてのカテゴリー" in full_text_search):
            print(f"    📖 Kindle版検索なし -> 物理本のページへ突入！")
            physical_asin = isbn13_to_asin(clean_isbn)
            physical_url = f"https://www.amazon.co.jp/dp/{physical_asin}"
            target_soup = get_soup(physical_url)
            target_url = physical_url
            
        # 2. 検索結果が出た場合 -> Kindle詳細ページへ
        else:
            result = soup_search.find("div", {"data-component-type": "s-search-result"})
            if result:
                asin = result.get("data-asin")
                if asin:
                    kindle_detail_url = f"https://www.amazon.co.jp/dp/{asin}"
                    target_soup = get_soup(kindle_detail_url)
                    target_url = kindle_detail_url

    # ==========================================
    # 🕵️‍♂️ ミッション2: ボタンの一括調査（KindleもAudibleも全部調べる！）
    # ==========================================
    if target_soup:
        info["amazon_url"] = target_url
        info["image_url"] = extract_image_from_soup(target_soup)
        if info["image_url"]:
            print("    📸 書影(画像)を確保しました！")
            
        # 【☆超強化】しんちゃんのHTML(aタグ)にも対応！
        buttons = target_soup.find_all(["span", "a"], class_=["a-button-toggle", "a-button-text"])
        for button in buttons:
            txt = button.get_text().replace('\n', '').replace(' ', '').replace('　', '')
            
            # --- Kindleのチェック ---
            if "Kindle" in txt or "電子書籍" in txt:
                info["has_kindle"] = True
                if button.find("i", class_="a-icon-kindle-unlimited") and ("￥0" in txt or "¥0" in txt):
                    info["is_unlimited"] = True
                    print("    🟢 ボタン判定: Kindle Unlimited クリア！")
                if button.find("i", class_="a-icon-prime"):
                    info["is_prime_reading"] = True
                    print("    🔵 ボタン判定: Prime Reading クリア！")
                    
            # --- Audibleのチェック (☆しんちゃんのHTML解析を完全再現！) ---
            if "Audible" in txt:
                info["has_audible"] = True
                if "￥0" in txt or "¥0" in txt:
                    info["is_audible"] = True
                    print("    🎧 ボタン判定: Audible 聴き放題 (￥0) を発見！")
                else:
                    print("    📙 ボタン判定: Audible 有料 を発見！")

        # 非ログイン時の隠しメッセージ「プライム会員も〜」を探す
        if info["has_kindle"] and not info["is_prime_reading"]:
            full_text = target_soup.get_text().replace('\n', '').replace(' ', '').replace('　', '')
            if "プライム会員も追加料金なしで" in full_text:
                info["is_prime_reading"] = True
                print("    🔵 補完判定: 全文テキストから Prime Reading を発見！")

    # ==========================================
    # 🎤 ミッション3: Audible専用検索 (最後のバックアップ)
    # ==========================================
    # もし詳細ページにAudibleボタンが無かった場合だけ、念のためAudibleストアを探す
    if not info["has_audible"]:
        print("    🔍 バックアップ: Audibleストア専用検索を行います")
        search_url_audible = f"https://www.amazon.co.jp/s?k={clean_isbn}&i=audible"
        soup_a_search = get_soup(search_url_audible)

        if soup_a_search:
            no_result_msg = soup_a_search.find("h3", class_="a-size-base")
            full_text_a_search = soup_a_search.get_text()
            if not ((no_result_msg and "結果は見つかりませんでした" in no_result_msg.get_text()) or \
               ("結果は見つかりませんでした" in full_text_a_search and "すべてのカテゴリー" in full_text_a_search)):
                
                result = soup_a_search.find("div", {"data-component-type": "s-search-result"})
                if result and result.get("data-asin"):
                    info["has_audible"] = True
                    audible_detail_url = f"https://www.amazon.co.jp/dp/{result.get('data-asin')}"
                    print(f"    🎤 Audible専用検索で発見! 詳細チェックへ")
                    
                    soup_a_detail = get_soup(audible_detail_url)
                    if soup_a_detail:
                        if "dp/" not in info["amazon_url"]: info["amazon_url"] = audible_detail_url
                        if not info["image_url"]: info["image_url"] = extract_image_from_soup(soup_a_detail)
                            
                        buttons = soup_a_detail.find_all(["span", "a"], class_=["a-button-toggle", "a-button-text"])
                        for button in buttons:
                            txt = button.get_text().replace('\n', '').replace(' ', '').replace('　', '')
                            if "Audible" in txt:
                                if "￥0" in txt or "¥0" in txt:
                                    info["is_audible"] = True
                                    print("    🎧 ボタン判定: Audible 聴き放題 (￥0) 発見！")

    return info