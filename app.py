# app.py
import threading
import time
import urllib.request
import webbrowser

from cato_helper import create_app

PORT = 5000


def open_browser_when_ready():
    """Flask サーバが立ち上がるまで待ってからブラウザを開く。"""
    url = f"http://127.0.0.1:{PORT}/"

    while True:
        try:
            # サーバに軽くアクセスしてみて、応答が返ってくれば OK
            with urllib.request.urlopen(url, timeout=1):
                pass
            break
        except Exception:
            # まだ立ち上がってない場合は少し待って再トライ
            time.sleep(0.3)

    # サーバ準備完了したらブラウザでタブを開く
    webbrowser.open(url)


if __name__ == "__main__":
    app = create_app()

    # サーバ起動を待ちつつ、準備できたらブラウザを開くスレッドを起動
    threading.Thread(
        target=open_browser_when_ready,
        daemon=True,
    ).start()

    # リローダーが二重起動させないように
    app.run(port=PORT, debug=True, use_reloader=False)
