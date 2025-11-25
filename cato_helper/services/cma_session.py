# cato_helper/services/cma_session.py
"""CMA へのログインとセッション情報の管理を行うモジュール。

Playwright を使って、
- cc.catonetworks.com → テナントのログイン画面 → CMA ダッシュボード
まで遷移し、ログイン済みセッションを STATE_FILE に保存します。

また、ログイン後には GraphQL の loginState を叩き、
ログイン先アカウントの accountName を取得するユーティリティも提供します。
"""

from __future__ import annotations
from .cma_queries import LOGIN_STATE_QUERY # type: ignore[reportUnknownMemberType]
from .response_store import save_response
from typing import Any

import json
import os
import re
from pathlib import Path
from typing import Any, Final

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .cma_account_map import resolve_account_display_name

# --- ログイン情報 / 設定値 ---

TENANT: Final[str] = os.getenv("CATO_TENANT", "kevoits")

# 最初にアクセスする共通ログインポータル
CC_LOGIN_URL: Final[str] = "https://cc.catonetworks.com"

# ログイン完了判定に使うテナント CMA の URL パターン
CMA_DASHBOARD_PATTERN: Final[str] = rf"https://{TENANT}\.cc\.catonetworks\.com/.*#/account/.*"

# GraphQL エンドポイント
CMA_GRAPHQL_URL: Final[str] = f"https://{TENANT}.cc.catonetworks.com/api/v1/graphql"

# このツールと同じディレクトリに state ファイルを置く
STATE_FILE = Path("cato_state.json")

LOGIN_PROFILE_FILE: Final[Path] = Path(__file__).with_name("login_profiles.json")

# loginState のキャッシュ（プロセス内でのみ有効）
_cached_login_state: dict[str, Any] | None = None




def load_login_profiles() -> dict[str, dict[str, str]]:
    """プロファイル一覧をファイルから読み込む。

    Returns:
        {"profile_name": {"EMAIL": "...", "PASSWORD": "..."}, ...}

    Raises:
        RuntimeError: ファイル欠損や JSON フォーマット不正、プロファイル未定義時。
    """

    if not LOGIN_PROFILE_FILE.exists():
        raise RuntimeError(
            "CMA ログイン用のプロファイルファイルが存在しません。\n"
            f"{LOGIN_PROFILE_FILE} を作成し、EMAIL/PASSWORD を設定してください。"
        )

    try:
        with LOGIN_PROFILE_FILE.open("r", encoding="utf-8") as f:
            profiles = json.load(f)
    except json.JSONDecodeError as e:  # noqa: BLE001
        raise RuntimeError(
            f"プロファイルファイルの JSON パースに失敗しました: {e}"
        ) from e

    if not isinstance(profiles, dict) or not profiles:
        raise RuntimeError("プロファイルが定義されていません。少なくとも1件定義してください。")

    return profiles # type: ignore[reportUnknownMemberType]

def resolve_login_profile(profile_name: str | None) -> tuple[str, str]:
    """指定されたプロファイルから EMAIL / PASSWORD を取得する。"""

    if not profile_name:
        raise RuntimeError("CMA ログイン用のプロファイル名が指定されていません。")

    profiles = load_login_profiles()
    profile = profiles.get(profile_name)
    if profile is None:
        raise RuntimeError(f"指定されたプロファイル '{profile_name}' は存在しません。")

    email = profile.get("EMAIL")
    password = profile.get("PASSWORD")

    return str(email), str(password)


def has_cma_state() -> bool:
    """CMA ログイン済みセッションが保存済みかどうか。"""
    return STATE_FILE.exists()


def cleanup_cma_state() -> None:
    """保存済みの CMA セッション情報を削除する。

    app.py 終了時に呼び出されることを想定。
    """
    global _cached_login_state
    _cached_login_state = None

    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
    except Exception:
        # 終了処理なので、失敗してもアプリには影響しないように握りつぶす
        pass


def _build_requests_session_from_state() -> requests.Session:
    if not STATE_FILE.exists():
        raise RuntimeError("CMA state file not found")

    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))

    tenant_host = f"{TENANT}.cc.catonetworks.com"

    # このリクエストで送りたい Cookie を手動で選別して 1 本のヘッダにする
    cookie_pairs: list[str] = []
    for c in state.get("cookies", []):
        domain = c.get("domain")
        name = c.get("name")
        value = c.get("value")

        if not name or value is None:
            continue

        # GraphQL に関係ありそうなドメインだけ残す
        if domain not in (
            tenant_host,
            ".catonetworks.com",
            f".{tenant_host}",
        ):
            continue

        cookie_pairs.append(f"{name}={value}")

    cookie_header = "; ".join(cookie_pairs)

    sess = requests.Session()
    sess.headers.update({
        "Cookie": cookie_header,
        "Content-Type": "application/json",
        "Origin": f"https://{tenant_host}",
        "Referer": f"https://{tenant_host}/?",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36"
        ),
    })

    print("=== BUILT COOKIE HEADER ===")
    print(cookie_header)

    return sess



from .response_store import save_response
from typing import Any

def fetch_login_state() -> dict[str, Any]:
    """GraphQL の loginState を叩いてログイン状態を取得する。"""
    print("=== FETCH_LOGIN_STATE CALLED ===")

    sess = _build_requests_session_from_state()
    print("Session built OK")

    payload: dict[str, Any] = {
        "operationName": "loginState",
        "variables": {"authcode": None, "authstate": None},
        "query": LOGIN_STATE_QUERY,
    }

    try:
        resp = sess.post(CMA_GRAPHQL_URL, json=payload, timeout=30)  # type: ignore[reportUnknownMemberType]

        print(">>> request url:", resp.request.url)
        print(">>> request headers:", resp.request.headers)
        print(">>> cookie header:", resp.request.headers.get("Cookie"))

        print(f"GraphQL status: {resp.status_code}")
    except Exception as e:  # 通信レベルで失敗
        print(f"[fetch_login_state] GraphQL request failed: {e!r}")
        # ここでも一応「リクエスト失敗情報」を保存しておく
        save_response("login_state_error", {"stage": "request", "error": str(e)})
        # 上には投げておく（get_cma_status が catch する）
        raise

    text = resp.text

    # まずは「生のレスポンス」を元に JSON を組み立てる
    try:
        data = resp.json()
        print("[fetch_login_state] JSON parsed OK")
    except Exception as e:
        print(f"[fetch_login_state] JSON parse error: {e!r}")
        # JSON としてパースできない場合も「生テキスト」を保存しておく
        data = {
            "raw_text": text,
            "json_error": str(e),
        }

    # ★ 成功／失敗に関わらず、とにかく保存する
    save_path = save_response("login_state", data)
    print(f"[fetch_login_state] response saved to {save_path}")

    # ここで HTTP エラーがあれば例外にする（上で保存は済んでいる）
    try:
        resp.raise_for_status()
    except Exception as e:
        print(f"[fetch_login_state] HTTP error: {e!r}")
        # get_cma_status() から見えるように例外は投げ直す
        raise

    # 正常ケースだけ loginState を返しつつ、キャッシュに乗せる
    if isinstance(data, dict):
        login_state = data.get("data", {}).get("loginState", {})  # type: ignore[reportUnknownMemberType]
    else:
        login_state = {}

    global _cached_login_state
    _cached_login_state = login_state

    return login_state


def get_cma_status() -> dict[str, Any]:
    """CMA ログイン状態 + 表示用アカウント名を返す。

    戻り値の例:
        {
            "logged_in": true,
            "account_name": "E221100280",
            "account_display_name": "E221100280（Altius Link 検証環境）",
            "error": null
        }
    """
    if not has_cma_state():
        return {
            "logged_in": False,
            "account_name": None,
            "account_display_name": None,
            "error": None,
        }

    try:
        global _cached_login_state
        login_state = _cached_login_state
        if not login_state:
            # まだ一度も取得していない場合だけ GraphQL を叩く
            login_state = fetch_login_state()
        # login_state は dict を想定
        account_name = login_state.get("accountName") if isinstance(login_state, dict) else None
        display_name = resolve_account_display_name(account_name)
        return {
            "logged_in": True,
            "account_name": account_name,
            "account_display_name": display_name,
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
        # ログインは多分できているが、loginState 取得に失敗した場合
        return {
            "logged_in": True,
            "account_name": None,
            "account_display_name": None,
            "error": str(e),
        }


def login_via_playwright(profile_name: str | None) -> None:
    """Playwright を使って CMA にログインし、セッション情報を保存する。

    - ブラウザウィンドウが立ち上がる（headless=False）ので、
      reCAPTCHA や MFA が出た場合は手動で対応してください。
    - ログイン完了後、CMA ダッシュボード URL に到達したら
      STATE_FILE に storage_state を保存して、ブラウザを閉じます。
    """
    # ログインし直すので loginState キャッシュはクリア
    global _cached_login_state
    _cached_login_state = None

    email, password = resolve_login_profile(profile_name)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=150)
        context = browser.new_context()
        page = context.new_page()

        # ① https://cc.catonetworks.com にアクセス
        print("① cc.catonetworks.com にアクセス中...")
        page.goto(CC_LOGIN_URL)

        # ② メールアドレス入力 → Next ボタンクリック
        try:
            print("② メールアドレス入力欄 (#username) を待機...")
            page.wait_for_selector('input#username[name="username"]', timeout=30_000)

            print("　メールアドレスを入力します...")
            page.fill('#username', email)

            print("　Next ボタンをクリックします...")
            next_button_selector = 'input.btn-submit[name="submit"][value="Next"]'
            page.click(next_button_selector)

        except PlaywrightTimeoutError:
            print(
                "　メール入力欄 or Next ボタンが見つからなかったので、このステップはスキップします。"
                "（既にログイン済みかもしれません）"
            )

        # ③ メール＋パスワード入力 → Log in クリック
        try:
            print("③ ユーザー名/メール＋パスワード入力欄を待機...")

            page.wait_for_url(
                re.compile(
                    r"auth\.catonetworks\.com|auth\." + re.escape(TENANT) + r"\.catonetworks\.com"
                ),
                timeout=30_000,
            )

            page.wait_for_selector('input[name="username"]', timeout=30_000)
            page.wait_for_selector('input[name="password"]', timeout=30_000)

            print("　username（メールアドレス）を入力します...")
            page.fill('input[name="username"]', email)

            print("　パスワードを入力します...")
            page.fill('input[name="password"]', password)

            print("　Log in ボタンをクリックします...")
            login_button_selector = 'input.btn-submit[name="submit"][value="Log in"]'
            page.click(login_button_selector)

            print("　→ Log in を自動クリックしました。")
            print("　※ reCAPTCHA が出た場合はブラウザ上で手動で対応してください。")

        except PlaywrightTimeoutError:
            print(
                "　username/password フォームが表示されなかったので、このステップはスキップします。"
                "（SSO などで既にログイン済みの可能性があります）"
            )

        # ④ ログイン完了検知（CMA ダッシュボード URL）
        print("④ ログイン完了（CMA ダッシュボード）URL を待ちます...")
        page.wait_for_url(
            re.compile(CMA_DASHBOARD_PATTERN),
            timeout=5 * 60 * 1000,
        )
        print("　CMA ダッシュボードに到達しました。ログイン完了とみなします。")

        # ログイン済みセッションを保存
        context.storage_state(path=str(STATE_FILE))
        print(f"　ログイン済みセッションを {STATE_FILE} に保存しました。")

        # ブラウザを閉じる
        browser.close()
