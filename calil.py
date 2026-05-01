import requests
import time
from xml.etree import ElementTree

def _get_api_key(app_key=None):
    """APIキーをst.secrets → 引数の順で取得する"""
    if app_key:
        return app_key
    try:
        import streamlit as st
        return st.secrets["CALIL_API_KEY"]
    except Exception:
        raise RuntimeError("Calil APIキーが設定されていません。.streamlit/secrets.toml に CALIL_API_KEY を追加してください。")

def check_library_availability(isbn_list, system_id, app_key=None):
    """
    指定された図書館ID (system_id) で、リストにあるISBNの貸出状況を一括チェックする。
    ポーリングに対応し、2回目以降は session ID を使って問い合わせる。
    """
    if not system_id:
        return {}

    api_key = _get_api_key(app_key)
    url = "https://api.calil.jp/check"
    isbn_str = ",".join(isbn_list)

    params = {
        "appkey": api_key,
        "isbn": isbn_str,
        "systemid": system_id,
        "format": "json",
        "callback": "no",
    }

    print(f"🏛️ カーリルで蔵書確認開始... (ID: {system_id})")

    max_retries = 10

    for i in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                print(f"⚠️ APIエラー: {response.status_code}")
                return {}

            data = response.json()

            if data.get("continue") == 1:
                session_id = data.get("session")
                print(f"  ⏳ 集計中... ({i+1}/{max_retries})")
                params = {
                    "appkey": api_key,
                    "session": session_id,
                    "format": "json",
                    "callback": "no",
                }
                time.sleep(2.5)
                continue

            return data.get("books", {})

        except Exception as e:
            print(f"⚠️ カーリル通信エラー: {e}")
            return {}

    return {}


def search_system_id(pref, city, app_key=None):
    """
    都道府県と市町村から図書館システムIDを検索する。
    Library APIはデフォルトXML形式のため、JSON取得を試みてXMLにフォールバックする。
    """
    api_key = _get_api_key(app_key)
    url = "https://api.calil.jp/library"

    # まずJSON形式で試みる
    params = {
        "appkey": api_key,
        "pref": pref,
        "city": city,
        "format": "json",
        "callback": "no",
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code != 200:
            return None

        content_type = response.headers.get("content-type", "")

        # JSON形式で取得できた場合
        if "json" in content_type:
            libraries = response.json()
            if libraries:
                found_id = libraries[0].get("systemid")
                print(f"✅ ID発見(JSON): {found_id} ({libraries[0].get('systemname')})")
                return found_id

        # XMLが返ってきた場合のフォールバック処理
        root = ElementTree.fromstring(response.text)
        for lib in root.findall("Library"):
            systemid_el = lib.find("systemid")
            systemname_el = lib.find("systemname")
            if systemid_el is not None and systemid_el.text:
                found_id = systemid_el.text
                name = systemname_el.text if systemname_el is not None else ""
                print(f"✅ ID発見(XML): {found_id} ({name})")
                return found_id

    except Exception as e:
        print(f"⚠️ ID検索エラー: {e}")

    return None
