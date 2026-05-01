import streamlit as st
import pandas as pd
import os
import base64
import requests
import database
import calil
import urllib.parse
from PIL import Image

def _load_banner(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

def _load_char(path):
    """ウィザードカード用キャラクター画像をbase64で返す"""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

_char_b64 = {
    'buy':     _load_char("assets/1新品で本をかう.png"),
    'genre':   _load_char("assets/2ジャンルを検索.png"),
    'cheap':   _load_char("assets/3フリマサイト.png"),
    'ebook':   _load_char("assets/4電子書籍.png"),
    'audible': _load_char("assets/5Audible.png"),
    'library': _load_char("assets/6図書館.png"),
}

def _char_img_html(key, height=120):
    b64 = _char_b64.get(key, "")
    if not b64:
        return ""
    return (f'<div style="text-align:center;margin-bottom:0.2rem;">'
            f'<img src="data:image/png;base64,{b64}" '
            f'style="height:{height}px;width:auto;object-fit:contain;"/></div>')

COUNTER_FILE = "counter.txt"

def get_and_increment_counter():
    count = 0
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "r") as f:
            try:
                count = int(f.read().strip())
            except ValueError:
                count = 0
    
    if not st.session_state.get('has_counted', False):
        count += 1
        with open(COUNTER_FILE, "w") as f:
            f.write(str(count))
        st.session_state['has_counted'] = True
        
    return count

@st.cache_data(show_spinner=False)
def get_image(url):
    headers = {}
    if "ndlsearch.ndl.go.jp" in str(url):
        headers["Referer"] = "https://ndlsearch.ndl.go.jp/"
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return "https://placehold.jp/150x200.png?text=NO+IMAGE"

def get_lib_status_html(lib_keys):
    """図書館の蔵書状況をHTMLカラーバッジで返す（UIガイド準拠）"""
    if not lib_keys:
        return '<span style="background:#9e9e9e;color:white;padding:4px 10px;border-radius:6px;font-size:0.75rem;font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.15);">⚪️ 蔵書なし</span>'
    badges = []
    for lib_name, status in lib_keys.items():
        if status == "貸出可":
            style = "background:#4caf50;color:white;"
            label = f"🟢 {lib_name}: 貸出可"
        elif status == "貸出中":
            style = "background:#f44336;color:white;"
            label = f"🔴 {lib_name}: 貸出中"
        elif status == "蔵書なし":
            style = "background:#9e9e9e;color:white;"
            label = f"⚪️ {lib_name}: 蔵書なし"
        else:
            style = "background:#ff9800;color:white;"
            label = f"🟡 {lib_name}: {status}"
        badges.append(
            f'<span style="{style}padding:4px 10px;border-radius:6px;'
            f'font-size:0.75rem;font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.15);">'
            f'{label}</span>'
        )
    return "<br>".join(badges)

def get_badges_html(row):
    """データから6つの分類バッジ(HTML)を生成する"""
    badges = []
    
    _b = 'padding:3px 10px; border-radius:20px; font-size:0.72rem; font-weight:700;'
    if not row.get("has_kindle", False) and not row.get("has_audible", False):
        badges.append(f'<span style="background:#EDE0D4; color:#7A5C4A; {_b}">📚 物理本のみ</span>')
    else:
        has_kindle_free = False
        if row.get("is_prime_reading", False):
            badges.append(f'<span style="background:#4A7DC8; color:white; {_b}">🔵 Prime Reading</span>')
            has_kindle_free = True
        elif row.get("is_unlimited", False):
            badges.append(f'<span style="background:#5C9E72; color:white; {_b}">🟢 Kindle Unlimited</span>')
            has_kindle_free = True
        if row.get("has_kindle", False) and not has_kindle_free:
            badges.append(f'<span style="background:#5B8899; color:white; {_b}">📘 Kindle 有料</span>')
        if row.get("is_audible", False):
            badges.append(f'<span style="background:#C4880A; color:white; {_b}">🎧 Audible 聴き放題</span>')
        elif row.get("has_audible", False):
            badges.append(f'<span style="background:#C46E2A; color:white; {_b}">📙 Audible 有料</span>')
            
    return " ".join(badges)

# --- 1. ページ設定 ---
st.set_page_config(page_title="学長オススメ書籍 本の案内所", page_icon=Image.open("assets/Gemini_Generated_Image_br717bbr717bbr71.png"), layout="wide")

# --- 2. スタイル ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=BIZ+UDPGothic:wght@400;700&family=Zen+Maru+Gothic:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Zen Maru Gothic', 'UD デジタル 教科書体 NP-R', 'UD Digi Kyokasho NP-R', 'BIZ UDPGothic', sans-serif !important;
}

/* ページ全体フェードイン */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}
section[data-testid="stMain"] > div:first-child {
    animation: fadeInUp 0.5s ease-out;
}

/* 背景 */
.stApp { background-color: #EDD9BE !important; }
[data-testid="stSidebar"] { background-color: #FAF0E4 !important; }

/* メインテキスト (UDフォントの特性に合わせて少し大きめ・読みやすく) */
[data-testid="stMain"] p,
[data-testid="stMain"] li { color: #4A3322 !important; font-size: 1.05rem !important; line-height: 1.8 !important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] label { color: #5A3E2B !important; font-size: 1.0rem !important; }

/* 本棚カード */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
    border: 2px solid #D4A06A !important;
    box-shadow: 0 8px 28px rgba(93,64,55,0.22) !important;
    background-color: #FFFFFF !important;
    transition: transform 0.25s ease, box-shadow 0.25s ease !important;
    position: relative !important;
    /* 🌟 カードの枠線と高さをピシッと揃える強力な魔法 🌟 */
    height: 100% !important;
    flex-grow: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
    flex-grow: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: flex-start !important;
}
/* カード内の一番下の要素（読みたい！ボタン等）を一番下へ押し下げる */
div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] > div:last-child {
    margin-top: auto !important;
}
/* カラム自体の高さを揃える */
div[data-testid="stHorizontalBlock"] {
    align-items: stretch !important;
}
div[data-testid="column"] > div[data-testid="stVerticalBlock"] {
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
}

/* 🌟 書籍のタイトルと著者の高さを固定する魔法 🌟 */
.book-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #4A3322;
    margin-bottom: 0.3rem;
    margin-top: 0.5rem;
    display: -webkit-box;
    -webkit-line-clamp: 2; /* 2行までに制限 */
    -webkit-box-orient: vertical;
    overflow: hidden;
    line-height: 1.5;
    height: 3.0em; /* 常に2行分の高さを確保 */
}
.book-author {
    font-size: 0.8rem;
    color: #9A7A58;
    margin-bottom: 0.5rem;
    display: -webkit-box;
    -webkit-line-clamp: 1; /* 1行までに制限 */
    -webkit-box-orient: vertical;
    overflow: hidden;
    line-height: 1.5;
    height: 1.5em; /* 常に1行分の高さを確保 */
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-7px) !important;
    box-shadow: 0 14px 32px rgba(93,64,55,0.15) !important;
}

/* 🌟 書影（画像）をカードの中心に寄せる魔法 🌟 */
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stImage"] {
    display: flex !important;
    justify-content: center !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stImage"] img {
    margin: 0 auto !important;
}

/* 通常ボタン */
button[data-testid="baseButton-secondary"] {
    border-radius: 20px !important;
    border: 1.5px solid #D9C4AF !important;
    background-color: #FFFAF4 !important;
    color: #6B4C3B !important;
    font-family: 'Zen Maru Gothic', 'UD デジタル 教科書体 NP-R', 'BIZ UDPGothic', sans-serif !important;
    font-size: 1.0rem !important;
    font-weight: 700 !important;
    transition: all 0.2s ease !important;
}
button[data-testid="baseButton-secondary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 10px rgba(93,64,55,0.14) !important;
    background-color: #FFF4E6 !important;
    border-color: #C4A077 !important;
}

/* リンクボタン */
div[data-testid="stLinkButton"] > a {
    border-radius: 20px !important;
    border: 1.5px solid #D9C4AF !important;
    background-color: #FFFAF4 !important;
    color: #6B4C3B !important;
    font-family: 'Zen Maru Gothic', 'UD デジタル 教科書体 NP-R', 'BIZ UDPGothic', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.0rem !important;
    transition: all 0.2s ease !important;
    text-decoration: none !important;
}
div[data-testid="stLinkButton"] > a:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 10px rgba(93,64,55,0.14) !important;
    background-color: #FFF4E6 !important;
    border-color: #C4A077 !important;
}

/* Primaryボタン */
button[data-testid="baseButton-primary"] {
    border-radius: 20px !important;
    background: linear-gradient(135deg, #82B49B, #5A9278) !important;
    color: #FFFFFF !important;
    border: none !important;
    font-family: 'Zen Maru Gothic', 'UD デジタル 教科書体 NP-R', 'BIZ UDPGothic', sans-serif !important;
    font-size: 0.92rem !important;
    font-weight: 700 !important;
    box-shadow: 0 3px 10px rgba(90,146,120,0.35) !important;
    transition: all 0.2s ease !important;
}
button[data-testid="baseButton-primary"]:hover {
    background: linear-gradient(135deg, #6A9A82, #4A8268) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 7px 18px rgba(90,146,120,0.45) !important;
}

/* 書影 */
[data-testid="stImage"] {
    display: flex;
    justify-content: center;
    margin-bottom: 0.8rem;
}
[data-testid="stImage"] img {
    height: 220px !important;
    width: 100% !important;
    object-fit: contain !important;
    border-radius: 8px;
}

/* お気に入りボタン（右上に浮かせる） */
div[data-testid="stVerticalBlockBorderWrapper"] button:has(p:contains("♡")),
div[data-testid="stVerticalBlockBorderWrapper"] button:has(p:contains("💖")) {
    position: absolute !important;
    top: 10px !important;
    right: 10px !important;
    z-index: 10 !important;
    border-radius: 50% !important;
    width: 44px !important;
    height: 44px !important;
    min-width: 44px !important;
    padding: 0 !important;
    background-color: rgba(255,255,255,0.92) !important;
    border: 2px solid #FFCDD2 !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.12) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button:has(p:contains("♡")) p,
div[data-testid="stVerticalBlockBorderWrapper"] button:has(p:contains("💖")) p {
    font-size: 1.4rem !important;
    line-height: 1 !important;
}

/* サイドバーヘッダー */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #6B4828 !important;
    border-bottom: 2px solid #E4C89A !important;
    padding-bottom: 0.3rem !important;
    font-size: 1.05rem !important;
    margin-bottom: 0.7rem !important;
}

/* ── バナー下の余白を詰める ── */
iframe {
    display: block !important;
    margin-bottom: -2.8rem !important;
}

/* ── スマホ 2列 ── */
@media screen and (max-width: 800px) {
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(4)),
    div[data-testid="stColumnLayout"]:has(> div:nth-child(4)) {
        flex-wrap: wrap !important;
    }
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) > div[data-testid="column"],
    div[data-testid="stColumnLayout"]:has(> div:nth-child(4)) > div[data-testid="column"] {
        width: calc(50% - 1rem) !important;
        flex: 1 1 calc(50% - 1rem) !important;
        min-width: calc(50% - 1rem) !important;
        max-width: calc(50% - 0.5rem) !important;
        margin-bottom: 1rem !important;
    }
}
</style>
""", unsafe_allow_html=True)
_banner_b64 = _load_banner("assets/本の案内所　バナー.png")
visitor_count = get_and_increment_counter()

st.components.v1.html(f"""
<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@700;900&family=Zen+Maru+Gothic:wght@400;500;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after {{margin:0;padding:0;box-sizing:border-box;}}
:root {{
  --cream:#FDF6E8;
  --espresso:#2B1800;--warm:#6B4830;
  --amber:#C8922A;--sage:#7BAF8E;--border:#D4B060;
}}
body {{font-family:'Zen Maru Gothic',sans-serif;background:transparent;}}

/* ── バナー全幅: 画像を背景として敷く ── */
.hero {{
  position:relative;
  height:220px;
  border-radius:22px;overflow:hidden;
  border:2px solid var(--border);
  box-shadow:0 1px 0 rgba(255,255,255,0.9) inset,0 6px 28px rgba(60,30,5,0.14);
  background:var(--cream);
}}
/* 画像: 枠全体にピッタリ広げる（変形させない美しい魔法） */
.banner-img {{
  position:absolute;inset:0;
  width:100%;height:100%;
  object-fit:cover;
  object-position:center center;
}}
/* 目隠し（グラデーション）を消して、画像をそのまま見せる */
.banner-fade {{
  display:none; /* 左側をクリーム色で塗りつぶしていた犯人 */
}}
/* テキスト */
.txt {{
  position:absolute;inset:0;z-index:2;
  display:flex;flex-direction:column;
  justify-content:center;
  align-items:center; /* 中央に寄せる魔法 */
  text-align:center;  /* 文字を中央揃えに */
  padding:1.4rem;
  width:100%; /* 全体に広げる */
}}
.visitor-counter {{
  font-size:0.8rem;
  color:var(--warm);
  background:rgba(253,246,232,0.65);
  padding:0.25rem 0.8rem;
  border-radius:12px;
  margin-top:0.6rem;
  display:inline-block;
  font-weight:500;
  animation:slideUp 0.4s ease both;animation-delay:0.35s;
}}
.visitor-counter span {{
  font-weight:900;
  color:var(--amber);
  font-size:1.1rem;
}}
h1 {{
  font-family:'Noto Serif JP',serif;
  font-size:1.85rem;font-weight:900;
  color:var(--espresso);line-height:1.2;
  animation:slideUp 0.4s ease both;animation-delay:0.08s;
}}
.subtitle {{
  font-size:1rem;font-weight:500;color:var(--warm);
  display:block;margin-top:3px;
}}
.rule {{
  width:38px;height:3px;
  background:linear-gradient(to right,var(--amber),var(--sage));
  border-radius:2px;margin:0.4rem auto; /* 線を真ん中に配置 */
}}
.tagline {{
  font-size:0.82rem;color:var(--warm);line-height:1.85;
  animation:slideUp 0.4s ease both;animation-delay:0.22s;
}}
.tagline strong {{color:var(--espresso);font-weight:700;}}
@keyframes slideUp {{
  from {{opacity:0;transform:translateY(10px);}}
  to   {{opacity:1;transform:translateY(0);}}
}}
</style>
</head>
<body>
<div class="hero">
  <img class="banner-img" src="data:image/png;base64,{_banner_b64}" alt="">
  <div class="banner-fade"></div>
  <div class="txt">
    <h1>学長オススメ書籍<span class="subtitle">本の案内所</span></h1>
    <div class="rule"></div>
    <p class="tagline">
      学長がおすすめした本と、あなたをつなぐ案内所。<br>
      <strong>読んでみたい、借りてみたい、大切にお迎えしたい――あなたにぴったりの方法で。</strong>
    </p>
    <div><span class="visitor-counter">あなたは <span>{visitor_count}</span> 人目の訪問者です。ようこそ！</span></div>
  </div>
</div>
</body>
</html>
""", height=228, scrolling=False)

# --- 3. データ読み込み ---
df = database.get_all_books()

CATEGORY_ORDER = [
    'お金の基礎教養', 'お金のしくみと歴史', '税金関連', '保険関連', '家賃を安くする',
    '投資の基本', '株式投資基礎', 'バリュー株投資', 'インデックス投資', '米国株投資', '投機の教科書',
    '不動産基礎知識', '不動産投資',
    '哲学・考え方', '時間', '人間関係', '健康',
    '転職', '経営', 'マーケティングスキル', 'ライティングスキル',
    'プログラミングスキル', 'デザインスキル', '子ども向け',
]

# ─── セッション初期化 ──────────────────────────────────────────────
for _k, _v in [
    ('wizard_mode',        'top'),
    ('availability_data',  {}),
    ('system_id',          ''),
    ('last_searched_city', ''),
    ('lib_step',           'select'),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─── 共通: 書籍グリッド描画 ────────────────────────────────────────
def render_book_grid(books_df, show_wishlist_btn=False, grid_key_suffix=""):
    if books_df.empty:
        st.info("条件に一致する本がありません。")
        return
    st.write(f"📚 **{len(books_df)} 冊**が見つかりました")
    avail    = st.session_state.get('availability_data', {})
    sys_id   = st.session_state.get('system_id', '')
    mode_key = st.session_state.get('wizard_mode', 'top') + grid_key_suffix
    COLS = 4
    for i in range(0, len(books_df), COLS):
        cols = st.columns(COLS)
        for j in range(COLS):
            if i + j >= len(books_df):
                break
            row      = books_df.iloc[i + j].to_dict()
            isbn_str = str(row['isbn'])
            with cols[j]:
                with st.container(border=True):
                    # 1. まず画像を一番上に配置（隙間ゼロ）
                    st.image(get_image(row["image_url"]))

                    # 2. お気に入りボタンとタイトルを横並びにする（♡を左に）
                    f_col, t_col = st.columns([1, 5])
                    with f_col:
                        if database.is_favorite(isbn_str):
                            if st.button("💖", key=f"fav_{isbn_str}_{mode_key}", help="お気に入り解除"):
                                database.toggle_favorite(isbn_str)
                                st.rerun()
                        else:
                            if st.button("♡", key=f"fav_{isbn_str}_{mode_key}", help="お気に入り追加"):
                                database.toggle_favorite(isbn_str)
                                st.rerun()
                    with t_col:
                        st.markdown(f'<div class="book-title">{row["title"]}</div>', unsafe_allow_html=True)

                    # 3. 著者名などを続ける
                    st.markdown(f'<div class="book-author">{row["author"]}</div>', unsafe_allow_html=True)
                    st.markdown(get_badges_html(row), unsafe_allow_html=True)
                    st.write("")

                    if show_wishlist_btn:
                        # 図書館モード: リスト追加ボタン
                        in_wl    = database.is_in_wishlist(isbn_str)
                        wl_count = len(database.get_wishlist())
                        if in_wl:
                            if st.button("✅ 選択解除", key=f"wl_{isbn_str}_{mode_key}",
                                         use_container_width=True):
                                database.remove_from_wishlist(isbn_str)
                                st.rerun()
                        else:
                            full = wl_count >= database.WISHLIST_MAX
                            lbl  = "🏛️ 図書館リストに追加" if not full else f"🈵 上限({database.WISHLIST_MAX}冊)"
                            if st.button(lbl, key=f"wl_{isbn_str}_{mode_key}",
                                         disabled=full, use_container_width=True):
                                database.add_to_wishlist(isbn_str)
                                st.rerun()
                    else:
                        # 通常モード: ポップオーバー
                        with st.popover("📖 読みたい！", use_container_width=True):
                            hp_anchor = row.get('hp_anchor', '')
                            if pd.notna(hp_anchor) and hp_anchor != "":
                                hp_url = f"https://liberaluni.com/recommended-books#{hp_anchor}"
                            else:
                                kw     = urllib.parse.quote(row['title'][:7])
                                hp_url = f"https://liberaluni.com/recommended-books#:~:text={kw}"

                            # 図書館蔵書状況（検索済みの場合）
                            if avail and isbn_str in avail and sys_id in avail.get(isbn_str, {}):
                                lib_keys    = avail[isbn_str][sys_id].get("libkey", {})
                                reserve_url = avail[isbn_str][sys_id].get("reserveurl", "")
                                st.markdown(get_lib_status_html(lib_keys), unsafe_allow_html=True)
                                if reserve_url:
                                    st.link_button("📖 図書館で予約する", reserve_url,
                                                   use_container_width=True)

                            c1, c2 = st.columns(2)
                            with c1:
                                st.link_button("🦁 学長HP", hp_url, use_container_width=True,
                                               help="学長HP内のこの本の紹介部分へ飛びます")
                            with c2:
                                st.link_button("🏛️ カーリル",
                                               f"https://calil.jp/book/{row['isbn']}",
                                               use_container_width=True)

                            st.caption("♻️ エコ・中古で探す")
                            et  = urllib.parse.quote(row['title'])
                            ei  = str(row['isbn'])
                            furima_url     = (
                                "https://furima.libecity.com/search?"
                                "category_id=&member_status=tora%2Cpanda%2Ciruka%2Cpengin%2Ckodomo"
                                f"&condition=&sort_key=&seller_uid=&min_price=&max_price=&now_on_sale="
                                f"&shipping_included=0&listing_type=&present_open=&keyword={et}"
                            )
                            valuebooks_url = f"https://www.valuebooks.jp/search?keyword={ei}"
                            mercari_url    = f"https://jp.mercari.com/search?keyword={ei}"
                            c3, c4, c5 = st.columns(3)
                            with c3: st.link_button("リベフリマ",    furima_url,     use_container_width=True)
                            with c4: st.link_button("メルカリ",      mercari_url,    use_container_width=True)
                            with c5: st.link_button("VALUE BOOKS",   valuebooks_url, use_container_width=True)


# ─── 現在のモード ───────────────────────────────────────────────────
mode = st.session_state['wizard_mode']

# ─── 戻るボタンと共通フィルター (TOP以外) ─────────────────────────────────────────
if mode != 'top':
    col_back, col_fav = st.columns([1, 1])
    with col_back:
        if st.button("← ホームに戻る", key="back_home"):
            st.session_state['wizard_mode'] = 'top'
            st.session_state['lib_step']    = 'select'
            st.rerun()
    with col_fav:
        # すべてのルートで使えるお気に入り絞り込みトグル
        is_fav_only = st.checkbox("💖 お気に入りだけを表示", value=st.session_state.get('filter_favorite', False), key="fav_toggle")
        st.session_state['filter_favorite'] = is_fav_only

    # チェックが入っていたら、この後のすべての処理で使う df をお気に入りのみに絞る
    if st.session_state.get('filter_favorite', False):
        fav_list = database.get_favorites()
        df = df[df["isbn"].isin(fav_list)]

    st.divider()


# ════════════════════════════════════════════════════════════════════
# 🏠 TOP スクリーン
# ════════════════════════════════════════════════════════════════════
if mode == 'top':
    # トップ画面専用の強力なCSSハックを挿入
    st.markdown("""
    <style>
    /* ウィザードコンテナ全体 (トップ画面の最後の枠ありコンテナ) */
    div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type {
        display: block !important; /* Flexbox魔法を無効化 */
        background-color: #FDF6E8 !important;
        border: 3px solid #D4B060 !important;
        border-radius: 22px !important;
        padding: 2.0rem 1.5rem !important;
        box-shadow: 0 6px 28px rgba(60,30,5,0.08) !important;
        margin-top: -10px !important; /* バナー画像に少し重ねる */
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type > div[data-testid="stVerticalBlock"] {
        display: block !important;
    }

    /* 全てのトップ画面セカンダリボタンを大きくカード風に */
    button[data-testid="baseButton-secondary"] {
        border-radius: 16px !important;
        padding: 1.5rem 0.5rem !important;
        height: auto !important;
        min-height: 90px !important;
        box-shadow: 0 6px 16px rgba(93,64,55,0.08) !important;
    }
    button[data-testid="baseButton-secondary"] p {
        font-size: 1.15rem !important; /* UDフォントに合わせて大きく */
        font-weight: 700 !important;
    }

    /* ボタンそれぞれの色付け (行と列で直接指定) */
    /* 1行目 */
    div[data-testid="stHorizontalBlock"]:nth-of-type(1) div[data-testid="column"]:nth-child(1) button {
        background-color: #FFF3E6 !important; border: 2px solid #EBC98A !important; color: #2B1800 !important;
    }
    div[data-testid="stHorizontalBlock"]:nth-of-type(1) div[data-testid="column"]:nth-child(2) button {
        background-color: #FFF9F0 !important; border: 2px solid #D9C4AF !important; color: #2B1800 !important;
    }
    div[data-testid="stHorizontalBlock"]:nth-of-type(1) div[data-testid="column"]:nth-child(3) button {
        background-color: #FDF6E8 !important; border: 2px solid #D4B060 !important; color: #2B1800 !important;
    }
    /* 2行目 */
    div[data-testid="stHorizontalBlock"]:nth-of-type(2) div[data-testid="column"]:nth-child(1) button {
        background-color: #EEF8F2 !important; border: 2px solid #A2D4B8 !important; color: #1A5C3A !important;
    }
    div[data-testid="stHorizontalBlock"]:nth-of-type(2) div[data-testid="column"]:nth-child(2) button {
        background-color: #F5F1E8 !important; border: 2px solid #CCBA88 !important; color: #2B1800 !important;
    }
    div[data-testid="stHorizontalBlock"]:nth-of-type(2) div[data-testid="column"]:nth-child(3) button {
        background-color: #FFFDF7 !important; border: 2px solid #EAD8A4 !important; color: #2B1800 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("""
        <div style="text-align:center;padding:0.5rem 0 1.2rem;">
          <p style="font-size:1.5rem;font-weight:700;color:#2B1800;margin:0 0 0.3rem;">
            どんな方法で、本と出会いますか？
          </p>
          <p style="font-size:0.88rem;color:#9A7A58;margin:0 0 1rem;">
            今のあなたに一番ぴったりな「本の入り口」を選んでくださいね
          </p>
          <div style="background:linear-gradient(to right,rgba(245,230,155,0.35),rgba(180,220,195,0.3));
                      border:1.5px dashed #BEA054;border-radius:10px;padding:0.6rem 1rem;
                      font-size:0.85rem;color:#6B4830;display:inline-block;margin-bottom:0.5rem;">
            🦁 <strong style="color:#2B1800;">本をお迎えする際は「学長HP」ボタン経由で</strong> → 学長への温かい応援になります
          </div>
        </div>
        """, unsafe_allow_html=True)
    
        col1, col2, col3 = st.columns(3)
        with col1:
            with st.container(border=True):
                st.markdown(_char_img_html('library'), unsafe_allow_html=True)
                if st.button("🏛️ 図書館で借りたい", use_container_width=True, key="btn_library"):
                    st.session_state['wizard_mode'] = 'library'
                    st.rerun()
                st.caption("最大10冊 × カーリル蔵書検索")
        with col2:
            with st.container(border=True):
                st.markdown(_char_img_html('audible'), unsafe_allow_html=True)
                if st.button("🎧 Audibleで聴きたい", use_container_width=True, key="btn_audible"):
                    st.session_state['wizard_mode'] = 'audible'
                    st.rerun()
                st.caption("聴き放題・有料の本を一覧")
        with col3:
            with st.container(border=True):
                st.markdown(_char_img_html('ebook'), unsafe_allow_html=True)
                if st.button("📱 電子書籍で読みたい", use_container_width=True, key="btn_ebook"):
                    st.session_state['wizard_mode'] = 'ebook'
                    st.rerun()
                st.caption("Kindle・Prime・Unlimited")

        col4, col5, col6 = st.columns(3)
        with col4:
            with st.container(border=True):
                st.markdown(_char_img_html('cheap'), unsafe_allow_html=True)
                if st.button("♻️ 安く手に入れたい", use_container_width=True, key="btn_cheap"):
                    st.session_state['wizard_mode'] = 'cheap'
                    st.rerun()
                st.caption("リベフリマ・メルカリ・VALUE BOOKS")
        with col5:
            with st.container(border=True):
                st.markdown(_char_img_html('genre'), unsafe_allow_html=True)
                if st.button("🔍 ジャンルから選ぶ", use_container_width=True, key="btn_genre"):
                    st.session_state['wizard_mode'] = 'genre'
                    st.rerun()
                st.caption("全カテゴリを一覧表示")
        with col6:
            with st.container(border=True):
                st.markdown(_char_img_html('buy'), unsafe_allow_html=True)
                if st.button("✨ 定価で買いたい", use_container_width=True, key="btn_buy"):
                    st.session_state['wizard_mode'] = 'buy'
                    st.rerun()
                st.caption("ジャンルを選んで学長HPへ")


# ════════════════════════════════════════════════════════════════════
# 📖 定価で買いたい
# ════════════════════════════════════════════════════════════════════
elif mode == 'buy':
    st.markdown("### 📖 定価で買いたい")
    st.caption("ジャンルを選んで、学長HPで購入リンクを確認しましょう")
    st.link_button("🦁 学長おすすめ書籍HPを見る",
                   "https://liberaluni.com/recommended-books")
    st.divider()

    available_cats = {str(c) for c in df["category"].dropna() if str(c) != ''}
    ordered_cats   = ["すべて"] + [c for c in CATEGORY_ORDER if c in available_cats]
    selected_cat   = st.selectbox("ジャンルを選ぶ", ordered_cats, key="buy_cat")
    filtered_df    = df if selected_cat == "すべて" else df[df["category"] == selected_cat]
    render_book_grid(filtered_df)


# ════════════════════════════════════════════════════════════════════
# 🎧 Audibleで聴きたい
# ════════════════════════════════════════════════════════════════════
elif mode == 'audible':
    st.markdown("### 🎧 Audibleで聴きたい")
    tab1, tab2 = st.tabs(["🎧 聴き放題 (Audible対象)", "📙 Audible版あり（有料含む）"])
    with tab1:
        st.info("🚧 **現在、聴き放題の判定魔法を調整中です！**\n\nより正確な情報をお届けできるよう、司書が一生懸命メンテナンスしています。完了までもうしばらくお待ちくださいね。")
    with tab2:
        render_book_grid(df[df["has_audible"] == True], grid_key_suffix="_tab2")


# ════════════════════════════════════════════════════════════════════
# 📱 電子書籍で読みたい
# ════════════════════════════════════════════════════════════════════
elif mode == 'ebook':
    st.markdown("### 📱 電子書籍で読みたい")
    tab1, tab2, tab3 = st.tabs(["🔵 Prime Reading", "🟢 Kindle Unlimited", "📘 Kindle版あり"])
    with tab1:
        render_book_grid(df[df["is_prime_reading"] == True], grid_key_suffix="_tab1")
    with tab2:
        render_book_grid(df[df["is_unlimited"] == True], grid_key_suffix="_tab2")
    with tab3:
        render_book_grid(df[df["has_kindle"] == True], grid_key_suffix="_tab3")


# ════════════════════════════════════════════════════════════════════
# 🏛️ 図書館で借りたい
# ════════════════════════════════════════════════════════════════════
elif mode == 'library':
    st.markdown("### 🏛️ 図書館で借りたい")
    lib_step = st.session_state.get('lib_step', 'select')

    # ─── 地域選択 ────────────────────────────────────
    with st.expander("📍 地域を選択する", expanded=True):
        try:
            api_key = st.secrets["CALIL_API_KEY"]
        except Exception:
            st.error("Calil APIキーが設定されていません。.streamlit/secrets.toml に CALIL_API_KEY を追加してください。")
            st.stop()

        city_data = None
        csv_path  = "data/city_code.csv"
        if os.path.exists(csv_path):
            try:
                try:
                    city_data = pd.read_csv(csv_path, encoding='cp932')
                except Exception:
                    city_data = pd.read_csv(csv_path, encoding='utf-8')
            except Exception:
                st.error("CSVファイルの読み込みに失敗しました")

        if city_data is not None:
            pref_list     = city_data.iloc[:, 1].dropna().unique()
            selected_pref = st.selectbox("都道府県", pref_list, key="lib_pref")
            filtered_data = city_data[
                (city_data.iloc[:, 1] == selected_pref) &
                (city_data.iloc[:, 2].notna())
            ]
            cities_in_pref = filtered_data.iloc[:, 2].unique()
            selected_city  = st.selectbox("市町村", cities_in_pref, key="lib_city")
        else:
            st.info("※ `data/city_code.csv` を配置すると選択式になります")
            selected_pref = st.text_input("都道府県 (例: 千葉県)")
            selected_city = st.text_input("市町村 (例: 八千代市)")

        st.caption("🔒 地域情報はこの端末内のみで使用されます。")

        current_sel = f"{selected_pref}_{selected_city}"
        if current_sel != st.session_state.get('last_searched_city'):
            st.session_state['last_searched_city'] = current_sel
            st.session_state['system_id'] = ''
            if selected_pref and selected_city:
                with st.spinner("図書館を検索中..."):
                    found_id = calil.search_system_id(selected_pref, selected_city, api_key)
                    st.session_state['system_id'] = found_id or ''

        system_id = st.session_state.get('system_id', '')
        if system_id:
            st.success(f"✅ {selected_city}の図書館が見つかりました")
        elif selected_pref and selected_city:
            st.caption("⚠️ この地域の図書館情報が見つかりませんでした")

    # ─── STEP: 本を選ぶ ──────────────────────────────
    if lib_step == 'select':
        wishlist  = database.get_wishlist()
        wl_count  = len(wishlist)
        system_id = st.session_state.get('system_id', '')

        # 赤いバー（primaryボタン）を絵本のようなパステルカラーにする魔法
        st.markdown("""
        <style>
        button[kind="primary"] {
            background-color: #FFDEB3 !important; /* 淡いパステルオレンジ */
            border: 2px solid #E8B478 !important; /* 枠線も少し濃いオレンジ */
            color: #6B4830 !important; /* 文字は優しいブラウン */
            font-weight: 700 !important;
            font-size: 1.1rem !important;
            border-radius: 12px !important;
            padding: 0.75rem !important;
            box-shadow: 0 4px 12px rgba(232, 180, 120, 0.2) !important;
        }
        button[kind="primary"]:hover {
            background-color: #FFD499 !important;
            border-color: #D69854 !important;
            color: #4A301D !important;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(
            f'<div style="background:#EEF8F2;border:1.5px solid #A2D4B8;border-radius:12px;'
            f'padding:0.75rem 1.2rem;margin:0.8rem 0;">'
            f'<span style="font-size:1rem;font-weight:700;color:#1A5C3A;">'
            f'📋 選択中: {wl_count} / {database.WISHLIST_MAX} 冊</span>'
            f'<span style="font-size:0.8rem;color:#4A8A6A;margin-left:0.8rem;">'
            f'下の本カードの「🏛️ 図書館リストに追加」を押してください</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        remaining     = database.get_remaining_search_count()
        check_disabled = (wl_count == 0) or (not system_id) or (remaining <= 0)
        if remaining <= 0:
            st.warning("⚠️ 検索上限(100回/時)に達しました。しばらく時間を置いてください。")

        if st.button(
            f"🏛️ 選択した {wl_count} 冊の蔵書を検索する",
            type="primary",
            disabled=check_disabled,
            use_container_width=True,
            key="lib_search_btn",
            help="地域の選択と、本のリスト追加が必要です" if check_disabled else "",
        ):
            isbn_list = database.get_wishlist()
            with st.spinner(f"図書館に問い合わせ中... ({len(isbn_list)} 冊)"):
                result = calil.check_library_availability(isbn_list, system_id, api_key)
                if result:
                    st.session_state['availability_data'] = result
            database.consume_search_count()
            st.session_state['lib_step'] = 'results'
            st.rerun()

        # バーの下に選択中の本のタイトルをリスト表示する
        if wl_count > 0:
            selected_titles = df[df["isbn"].isin(wishlist)]["title"].tolist()
            titles_html = "".join([
                f"<li style='color:#6B4830; font-size:0.9rem; margin-bottom:0.3rem; padding-left:0.5rem;'>"
                f"🔖 {t}</li>" for t in selected_titles
            ])
            st.markdown(
                f"<div style='background:#FDF6E8; border:1px dashed #D4B060; border-radius:12px; padding:1rem 1.2rem; margin-top:0.5rem;'>"
                f"<p style='margin:0 0 0.5rem 0; font-weight:700; color:#2B1800; font-size:0.95rem;'>お迎え待ちの本たち：</p>"
                f"<ul style='margin:0; padding:0; list-style-type:none;'>{titles_html}</ul>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.divider()
        render_book_grid(df, show_wishlist_btn=True)

    # ─── STEP: 検索結果 ──────────────────────────────
    elif lib_step == 'results':
        system_id   = st.session_state.get('system_id', '')
        avail_data  = st.session_state.get('availability_data', {})
        wishlist    = database.get_wishlist()
        all_books   = database.get_all_books()
        wl_books_df = all_books[all_books["isbn"].isin(wishlist)]

        if st.button("← 本の選択に戻る", key="lib_back_to_select"):
            st.session_state['lib_step'] = 'select'
            st.rerun()

        st.markdown("#### 🏛️ 蔵書状況の結果")
        header_cols = st.columns([4, 2, 2])
        header_cols[0].markdown("**本のタイトル**")
        header_cols[1].markdown("**蔵書状況**")
        header_cols[2].markdown("**予約**")
        st.divider()

        for _, r in wl_books_df.iterrows():
            isbn_val  = str(r['isbn'])
            row_cols  = st.columns([4, 2, 2])
            row_cols[0].write(r['title'][:28])
            if isbn_val in avail_data and system_id in avail_data.get(isbn_val, {}):
                lib_keys    = avail_data[isbn_val][system_id].get("libkey", {})
                reserve_url = avail_data[isbn_val][system_id].get("reserveurl", "")
                row_cols[1].markdown(get_lib_status_html(lib_keys), unsafe_allow_html=True)
                if reserve_url:
                    row_cols[2].link_button("📖 予約", reserve_url)
                else:
                    row_cols[2].write("—")
            else:
                row_cols[1].markdown(
                    '<span style="background:#9e9e9e;color:white;padding:3px 8px;'
                    'border-radius:6px;font-size:0.75rem;">⚪ 蔵書なし</span>',
                    unsafe_allow_html=True
                )
                row_cols[2].write("—")


# ════════════════════════════════════════════════════════════════════
# ♻️ 安く手に入れたい
# ════════════════════════════════════════════════════════════════════
elif mode == 'cheap':
    st.markdown("### ♻️ 安く手に入れたい")
    st.caption("リベフリマ・メルカリ・VALUE BOOKSで中古本を探しましょう")
    st.divider()
    render_book_grid(df)


# ════════════════════════════════════════════════════════════════════
# 🔍 ジャンルから選ぶ
# ════════════════════════════════════════════════════════════════════
elif mode == 'genre':
    st.markdown("### 🔍 ジャンルから選ぶ")

    available_cats = {str(c) for c in df["category"].dropna() if str(c) != ''}
    ordered_cats   = ["すべて"] + [c for c in CATEGORY_ORDER if c in available_cats]
    selected_cat   = st.selectbox("ジャンルを選ぶ", ordered_cats, key="genre_cat")
    filtered_df    = df if selected_cat == "すべて" else df[df["category"] == selected_cat]
    render_book_grid(filtered_df)
