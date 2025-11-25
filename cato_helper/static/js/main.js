console.log("Cato Helper Console loaded");

// 左メニューのセクション開閉
document.addEventListener("DOMContentLoaded", () => {
    const titles = document.querySelectorAll(".sidebar-section-title");

    // ==== CMA ログイン UI 制御 ====
    const cmaLoginButton = document.getElementById("cma-login-button");
    const cmaLogoutButton = document.getElementById("cma-logout-button");
    const cmaLoginStatus = document.getElementById("cma-login-status");
    const cmaProfileSelect = document.getElementById("cma-profile-select");

    let cmaStatusTimer = null;
    const defaultCmaLoginText = cmaLoginButton?.textContent;
    const profileStorageKey = "cato_helper_cma_profile_name";

    // 状態フラグ
    let isCmaLoginInProgress = false;
    let isCmaLoggedIn = false;
    let currentCmaProfileName = null;

    // 前回ログイン時のプロファイル名を localStorage から復元
    try {
        currentCmaProfileName = window.localStorage.getItem(profileStorageKey);
    } catch (e) {
        currentCmaProfileName = null;
    }

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

    function updateLogoutButtonState() {
        if (!cmaLogoutButton) return;
        // ログイン済みのときだけ押せる
        cmaLogoutButton.disabled = !isCmaLoggedIn;
    }

    // ログイン後のプロファイル表示（セレクトボックス非表示）
    function applyLoggedInProfileView() {
        if (!cmaProfileSelect) return;

        // select の親要素（＝カプセルっぽい薄い枠）ごと非表示にする
        const wrap = cmaProfileSelect.parentElement;
        if (wrap) {
            wrap.style.display = "none";
        } else {
            // 念のため：親が取れなかった場合は select 自体を消す
            cmaProfileSelect.style.display = "none";
        }
    }

    function applyLoggedOutProfileView() {
        if (!cmaProfileSelect) return;

        const wrap = cmaProfileSelect.parentElement;
        if (wrap) {
            // display の指定を元に戻す（CSS のデフォルトに任せる）
            wrap.style.display = "";
        } else {
            cmaProfileSelect.style.display = "";
        }
    }



    // CMAログイン状態取得
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
                // ★ ログイン済み
                isCmaLoggedIn = true;
                isCmaLoginInProgress = false;

                // ステータスタグには「環境名」を表示する
                // 1) ログイン時に選択されたプロファイル名（= 環境名）
                // 2) それが無ければサーバから返る account_display_name
                // 3) どちらも無ければ従来どおり「ログイン済み」
                let envLabel = currentCmaProfileName;
                if (!envLabel && data.account_display_name) {
                    envLabel = data.account_display_name;
                }
                if (!envLabel) {
                    envLabel = "ログイン済み";
                }
                cmaLoginStatus.textContent = envLabel;
                setStatusClass("login-status-on");

                // ログイン済みならプロファイルは “環境名だけ表示”
                if (currentCmaProfileName && cmaProfileSelect) {
                    applyLoggedInProfileView();
                }

                if (cmaStatusTimer) {
                    clearInterval(cmaStatusTimer);
                    cmaStatusTimer = null;
                }

                // ★ ログインボタンをグレー見た目に
                if (cmaLoginButton) {
                    cmaLoginButton.classList.add("btn-cma-login-logged-in");
                }

            } else {
                // 未ログイン or ログイン中
                isCmaLoggedIn = false;

                // ★ 未ログイン扱いなのでセレクトボックスを表示状態に戻す
                applyLoggedOutProfileView();

                if (isCmaLoginInProgress) {
                    cmaLoginStatus.textContent = "ログイン中";
                    setStatusClass("login-status-processing");
                } else {
                    cmaLoginStatus.textContent = "未ログイン";
                    setStatusClass("login-status-off");
                }

                // ★ 未ログイン時はグレー見た目クラスを外す
                if (cmaLoginButton) {
                    cmaLoginButton.classList.remove("btn-cma-login-logged-in");
                }
            }


            updateLogoutButtonState();
        } catch (e) {
            console.error("CMA status check error", e);
            cmaLoginStatus.textContent = "状態確認エラー";
            setStatusClass("login-status-off");
            isCmaLoggedIn = false;
            isCmaLoginInProgress = false;
            updateLogoutButtonState();
        }
    }

    // プロファイル一覧読み込み（未ログイン時に選択できるようにする）
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

            // 未ログイン時は選択可能
            cmaProfileSelect.disabled = isCmaLoggedIn;
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

    // ページ表示時：ステータス確認 & プロファイル取得
    if (cmaLoginStatus) {
        fetchCmaStatusOnce();
    }
    loadCmaProfiles();
    updateLogoutButtonState();

    // ログインボタン
    if (cmaLoginButton) {
        cmaLoginButton.addEventListener("click", async () => {
            try {
                const selectedProfile = cmaProfileSelect ? cmaProfileSelect.value : "";
                if (!selectedProfile) {
                    throw new Error("ログインプロファイルを選択してください。");
                }

                // 選択された環境名を保存
                currentCmaProfileName = selectedProfile;
                try {
                    window.localStorage.setItem(profileStorageKey, selectedProfile);
                } catch (e) {
                    console.warn("localStorage set error", e);
                }

                if (cmaStatusTimer) {
                    clearInterval(cmaStatusTimer);
                    cmaStatusTimer = null;
                }

                isCmaLoginInProgress = true;
                isCmaLoggedIn = false;

                cmaLoginButton.disabled = true;
                if (cmaProfileSelect) {
                    cmaProfileSelect.disabled = true;
                }
                if (cmaLoginStatus) {
                    cmaLoginStatus.textContent = "ログイン中";
                    setStatusClass("login-status-processing");
                }
                updateLogoutButtonState();

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
                    isCmaLoginInProgress = false;
                    await fetchCmaStatusOnce();
                    cmaLoginButton.disabled = false;
                    cmaLoginButton.textContent = defaultCmaLoginText;
                } else if (data.status === "started") {
                    // ログイン中 → 5秒ごとにステータスをポーリング
                    if (!cmaStatusTimer) {
                        cmaStatusTimer = setInterval(fetchCmaStatusOnce, 5000);
                    }
                } else if (data.status === "error") {
                    throw new Error(data.message || "ログイン開始に失敗しました。");
                } else {
                    cmaLoginStatus.textContent = "状態不明";
                    setStatusClass("login-status-off");
                    cmaLoginButton.disabled = false;
                    cmaLoginButton.textContent = defaultCmaLoginText;
                    isCmaLoginInProgress = false;
                }

                updateLogoutButtonState();
            } catch (e) {
                console.error("CMA login error", e);
                if (cmaLoginStatus) {
                    cmaLoginStatus.textContent = e?.message || "エラー";
                    setStatusClass("login-status-off");
                }
                isCmaLoginInProgress = false;
                isCmaLoggedIn = false;
                if (cmaProfileSelect) {
                    // ログインに失敗したら再度選択できるようにする
                    cmaProfileSelect.disabled = false;
                }
                cmaLoginButton.disabled = false;
                cmaLoginButton.textContent = defaultCmaLoginText;
                updateLogoutButtonState();
            }
        });
    }

    // ログアウトボタン
    if (cmaLogoutButton) {
        cmaLogoutButton.addEventListener("click", async () => {
            const ok = window.confirm("CMA からログアウトしますか？");
            if (!ok) return;

            cmaLogoutButton.disabled = true;
            if (cmaLoginStatus) {
                cmaLoginStatus.textContent = "ログアウト中...";
                setStatusClass("login-status-processing");
            }

            try {
                if (cmaStatusTimer) {
                    clearInterval(cmaStatusTimer);
                    cmaStatusTimer = null;
                }

                const res = await fetch("/cma/logout", { method: "POST" });
                if (!res.ok) {
                    throw new Error("ログアウトに失敗しました。");
                }

                // セッション・レスポンス削除 → 未ログイン状態に戻す
                isCmaLoggedIn = false;
                isCmaLoginInProgress = false;
                currentCmaProfileName = null;
                try {
                    window.localStorage.removeItem(profileStorageKey);
                } catch (e) {
                    console.warn("localStorage remove error", e);
                }

                if (cmaLoginStatus) {
                    cmaLoginStatus.textContent = "未ログイン";
                    setStatusClass("login-status-off");
                }

                // ★ ログアウトしたのでセレクトボックスを再表示
                applyLoggedOutProfileView();

                if (cmaProfileSelect) {
                    cmaProfileSelect.disabled = true;
                    cmaProfileSelect.innerHTML = "";
                    const opt = document.createElement("option");
                    opt.textContent = "読み込み中...";
                    cmaProfileSelect.appendChild(opt);
                }

                // プロファイルを再取得（未ログインなので再び選択可能にする）
                loadCmaProfiles();

            } catch (e) {
                console.error("CMA logout error", e);
                if (cmaLoginStatus) {
                    cmaLoginStatus.textContent = "ログアウトエラー";
                    setStatusClass("login-status-off");
                }
            } finally {
                if (cmaLoginButton) {
                    cmaLoginButton.disabled = false;
                    cmaLoginButton.textContent = defaultCmaLoginText;
                    // ログアウト後は「ログイン済み」見た目のクラスを外して通常色に戻す
                    cmaLoginButton.classList.remove("btn-cma-login-logged-in");
                }
                isCmaLoginInProgress = false;
                updateLogoutButtonState();
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
