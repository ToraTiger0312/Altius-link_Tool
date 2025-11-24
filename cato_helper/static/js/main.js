console.log("Cato Helper Console loaded");

// 左メニューのセクション開閉
document.addEventListener("DOMContentLoaded", () => {
    const titles = document.querySelectorAll(".sidebar-section-title");

    // ==== CMA ログイン UI 制御 ====
    const cmaLoginButton = document.getElementById("cma-login-button");
    const cmaLoginStatus = document.getElementById("cma-login-status");
    const cmaProfileSelect = document.getElementById("cma-profile-select");
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

    async function loadCmaProfiles() {
        if (!cmaProfileSelect) return;

        try {
            const res = await fetch("/cma/profiles");
            if (!res.ok) {
                throw new Error("HTTP " + res.status);
            }

            const data = await res.json();
            if (data.status !== "ok") {
                throw new Error(data.message || "プロファイル取得に失敗しました");
            }

            cmaProfileSelect.innerHTML = "";

            const placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = "選択してください";
            cmaProfileSelect.appendChild(placeholder);

            data.profiles.forEach((profile) => {
                const opt = document.createElement("option");
                opt.value = profile.name;
                opt.textContent = profile.name;
                cmaProfileSelect.appendChild(opt);
            });

            cmaProfileSelect.disabled = false;
        } catch (e) {
            console.error("プロファイル取得エラー", e);
            cmaProfileSelect.innerHTML = "";
            const opt = document.createElement("option");
            opt.textContent = "プロファイル読み込み失敗";
            cmaProfileSelect.appendChild(opt);
            cmaProfileSelect.disabled = true;

            if (cmaLoginStatus) {
                cmaLoginStatus.textContent = "プロファイル未設定";
                setStatusClass("login-status-off");
            }
        }
    }

    // ページ表示時にステータス確認とプロファイル取得を実行
    if (cmaLoginStatus) {
        fetchCmaStatusOnce();
    }
    loadCmaProfiles();

    if (cmaLoginButton) {
        cmaLoginButton.addEventListener("click", async () => {
            try {
                cmaLoginButton.disabled = true;
                cmaLoginButton.textContent = "ログイン処理中...";
                if (cmaLoginStatus) {
                    cmaLoginStatus.textContent = "ログイン処理中...";
                    setStatusClass("login-status-processing");
                }

                const selectedProfile = cmaProfileSelect ? cmaProfileSelect.value : "";
                if (!selectedProfile) {
                    throw new Error("ログインプロファイルを選択してください。");
                }

                const response = await fetch("/cma/login", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ profile: selectedProfile }),
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
                } else if (data.status === "error") {
                    throw new Error(data.message || "ログイン開始に失敗しました。");
                } else {
                    cmaLoginStatus.textContent = "状態不明";
                    setStatusClass("login-status-off");
                    cmaLoginButton.disabled = false;
                    cmaLoginButton.textContent = "CMAログイン";
                }
            } catch (e) {
                console.error("CMA login error", e);
                if (cmaLoginStatus) {
                    cmaLoginStatus.textContent = e?.message || "エラー";
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
