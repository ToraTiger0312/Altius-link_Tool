# app.py
import os
import threading
import time
import urllib.request
import webbrowser

from cato_helper import create_app

# ポート番号やデバッグモードは環境変数から変更できるようにしておく
PORT = int(os.environ.get("CATO_HELPER_PORT", 5000))
DEBUG = os.environ.get("CATO_HELPER_DEBUG", "1") == "1"


def open_browser_when_ready(timeout: int = 30) -> None:
    """Flask サーバが立ち上がるまで待ってからブラウザを開く。

    timeout 秒待っても応答がない場合はあきらめる。
    """
    url = f"http://127.0.0.1:{PORT}/"

    start = time.time()
    while True:
        try:
            with urllib.request.urlopen(url) as _:
                break
        except Exception:
            if time.time() - start > timeout:
                # あまり待ちすぎないようにする
                return
            time.sleep(0.5)

    webbrowser.open(url)


if __name__ == "__main__":
    app = create_app()

    # サーバ起動を待ちつつ、準備できたらブラウザを開くスレッドを起動
    threading.Thread(
        target=open_browser_when_ready,
        daemon=True,
    ).start()

    # リローダーが二重起動させないように
    app.run(port=PORT, debug=DEBUG, use_reloader=False)
