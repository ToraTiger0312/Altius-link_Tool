console.log("Cato Helper Console loaded");

// 左メニューのセクション開閉
document.addEventListener("DOMContentLoaded", () => {
    const titles = document.querySelectorAll(".sidebar-section-title");

    // ==== CMA ログイン UI 制御 ====
    const cmaLoginButton = document.getElementById("cma-login-button");
    const cmaLoginStatus = document.getElementById("cma-login-status");
    let cmaStatusTimer = null;

    function setStatusClass(mode) {
        if (!cmaLoginStatus) return;
        cmaLoginStatus.classList.remove(
            "login-status-off",
            "login-status-on",
            "login-status-processing"
        );
        if (mode) {
            cmaLoginStatus.classList.add(mode);
        }
    }

    async function fetchCmaStatusOnce() {
        if (!cmaLoginStatus) return;
        try {
            const res = await fetch("/cma/status");
            if (!res.ok) {
                throw new Error("HTTP " + res.status);
            }
            const data = await res.json();
            console.log("CMA status:", data);

            if (data.logged_in) {
                const name =
                    data.account_display_name ||
                    data.account_name ||
                    "ログイン済み";
                cmaLoginStatus.textContent = name;
                setStatusClass("login-status-on");
            } else {
                cmaLoginStatus.textContent = "未ログイン";
                setStatusClass("login-status-off");
            }
        } catch (e) {
            console.error("CMA status check error", e);
            cmaLoginStatus.textContent = "状態確認エラー";
            setStatusClass("login-status-off");
        }
    }

    // ページ表示時に一度ステータスをチェック
    if (cmaLoginStatus) {
        fetchCmaStatusOnce();
    }

    if (cmaLoginButton) {
        cmaLoginButton.addEventListener("click", async () => {
            try {
                cmaLoginButton.disabled = true;
                cmaLoginButton.textContent = "ログイン処理中...";
                if (cmaLoginStatus) {
                    cmaLoginStatus.textContent = "ログイン処理中...";
                    setStatusClass("login-status-processing");
                }

                const response = await fetch("/cma/login", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({}),
                });

                const data = await response.json();
                console.log("CMA login response:", data);

                if (data.status === "already_logged_in") {
                    // すでにログイン済みなら即ステータス確認
                    await fetchCmaStatusOnce();
                    cmaLoginButton.disabled = false;
                    cmaLoginButton.textContent = "CMAログイン";
                } else if (data.status === "started") {
                    // ログイン処理中 → 5秒ごとにステータスをポーリング
                    if (!cmaStatusTimer) {
                        cmaStatusTimer = setInterval(fetchCmaStatusOnce, 5000);
                    }
                } else {
                    cmaLoginStatus.textContent = "状態不明";
                    setStatusClass("login-status-off");
                    cmaLoginButton.disabled = false;
                    cmaLoginButton.textContent = "CMAログイン";
                }
            } catch (e) {
                console.error("CMA login error", e);
                if (cmaLoginStatus) {
                    cmaLoginStatus.textContent = "エラー";
                    setStatusClass("login-status-off");
                }
                cmaLoginButton.disabled = false;
                cmaLoginButton.textContent = "CMAログイン";
            }
        });
    }
    // ==== CMA ログイン UI 制御ここまで ====

    // ==== 終了ボタン ====
    const exitButton = document.getElementById("app-exit-button");
    if (exitButton) {
        exitButton.addEventListener("click", async () => {
            const ok = window.confirm("ツールを終了しますか？");
            if (!ok) return;

            try {
                await fetch("/shutdown", { method: "POST" });
            } catch (e) {
                console.error("shutdown error", e);
            } finally {
                // バックエンドが落ちればこれ以降の操作はできないので、
                // タブが閉じられなくても実害はほぼなし
                window.close();
            }
        });
    }


    // 左メニューのセクション開閉
    titles.forEach((title) => {
        title.addEventListener("click", () => {
            const section = title.closest(".sidebar-section");
            if (section) {
                section.classList.toggle("collapsed");
            }
        });
    });
});
