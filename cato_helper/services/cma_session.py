# cato_helper/services/cma_session.py
"""CMA へのログインとセッション情報の管理を行うモジュール。

Playwright を使って、
- cc.catonetworks.com → テナントのログイン画面 → CMA ダッシュボード
まで遷移し、ログイン済みセッションを STATE_FILE に保存します。

また、ログイン後には GraphQL の loginState を叩き、
ログイン先アカウントの accountName を取得するユーティリティも提供します。
"""

from __future__ import annotations
from .cma_queries import LOGIN_STATE_QUERY
from .response_store import save_response

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
CMA_GRAPHQL_URL: Final[str] = f"https://{TENANT}.cc.catonetworks.com/api/graphql"

# このツールと同じディレクトリに state ファイルを置く
STATE_FILE: Final[Path] = Path("cato_state.json")

# ★ 本番では環境変数などから読むのを推奨
EMAIL: Final[str] = os.getenv("CATO_EMAIL", "your-email@example.com")
PASSWORD: Final[str] = os.getenv("CATO_PASSWORD", "CHANGE_ME")


def has_cma_state() -> bool:
    """CMA ログイン済みセッションが保存済みかどうか。"""
    return STATE_FILE.exists()


def cleanup_cma_state() -> None:
    """保存済みの CMA セッション情報を削除する。

    app.py 終了時に呼び出されることを想定。
    """
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
    except Exception:
        # 終了処理なので、失敗してもアプリには影響しないように握りつぶす
        pass


def _build_requests_session_from_state() -> requests.Session:
    """Playwright の storage_state(JSON) から requests セッションを構築する。"""
    if not STATE_FILE.exists():
        raise RuntimeError("CMA の state ファイルが存在しません。まず CMA ログインを実行してください。")

    with STATE_FILE.open("r", encoding="utf-8") as f:
        state = json.load(f)

    cookies = state.get("cookies", [])
    sess = requests.Session()
    for c in cookies:
        # domain / path も設定しておく
        sess.cookies.set(c.get("name"), c.get("value"), domain=c.get("domain"), path=c.get("path", "/")) # type: ignore[reportUnknownMemberType]

    return sess


def fetch_login_state() -> dict[str, Any]:
    """GraphQL の loginState を叩いてログイン状態を取得する。"""
    sess = _build_requests_session_from_state()

    payload = { # type: ignore[reportUnknownMemberType]
        "operationName": "loginState",
        "variables": {"authcode": None, "authstate": None},
        "query": LOGIN_STATE_QUERY,
    }

    resp = sess.post(CMA_GRAPHQL_URL, json=payload, timeout=30) # type: ignore[reportUnknownMemberType]
    resp.raise_for_status()
    data = resp.json()

    # レスポンスを一時ファイルに保存
    save_response("login_state", data)

    return data.get("data", {}).get("loginState", {})


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
        login_state = fetch_login_state()
        account_name = login_state.get("accountName")
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


def login_via_playwright() -> None:
    """Playwright を使って CMA にログインし、セッション情報を保存する。

    - ブラウザウィンドウが立ち上がる（headless=False）ので、
      reCAPTCHA や MFA が出た場合は手動で対応してください。
    - ログイン完了後、CMA ダッシュボード URL に到達したら
      STATE_FILE に storage_state を保存して、ブラウザを閉じます。
    """

    # EMAIL / PASSWORD がそのままだと危険なので、簡易チェック
    if EMAIL == "your-email@example.com" or PASSWORD in ("CHANGE_ME", "", None):
        raise RuntimeError(
            """CMA ログイン用の EMAIL / PASSWORD が設定されていません。\n"""
            """環境変数 CATO_EMAIL / CATO_PASSWORD を設定するか、\n"""
            """cato_helper/services/cma_session.py 内の EMAIL / PASSWORD を\n"""
            """適切な値に書き換えてください。"""
        )

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
            page.fill('#username', EMAIL)

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
            page.fill('input[name="username"]', EMAIL)

            print("　パスワードを入力します...")
            page.fill('input[name="password"]', PASSWORD)

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
