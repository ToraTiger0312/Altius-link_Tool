// cato_helper/static/js/static_route.js

document.addEventListener("DOMContentLoaded", () => {
    // --- Network / Account タブを CMA ログイン必須にする ---

    function attachCmaGuardToLinks() {
        const guardedLinks = document.querySelectorAll("[data-requires-cma-login='true']");
        if (!guardedLinks.length) return;

        guardedLinks.forEach((link) => {
            link.addEventListener("click", async (ev) => {
                // 通常の画面遷移を一旦止める
                ev.preventDefault();

                try {
                    const res = await fetch("/cma/status");
                    if (!res.ok) {
                        throw new Error("HTTP " + res.status);
                    }
                    const data = await res.json();

                    if (data && data.logged_in) {
                        // ログイン済みならそのまま遷移
                        window.location.href = link.getAttribute("href") || "#";
                    } else {
                        alert("CMA にログインしてからこのメニューを利用してください。");
                    }
                } catch (e) {
                    console.error("CMA status check failed", e);
                    alert("CMA の状態確認に失敗しました。右上のログイン状態を確認してください。");
                }
            });
        });
    }

    attachCmaGuardToLinks();

    // --- Static Route 画面用の初期化処理 ---

    const pageRoot = document.getElementById("static-route-page");
    if (!pageRoot) {
        // このページではない場合は何もしない
        return;
    }

    const statusEl = document.getElementById("static-route-status");
    const reloadBtn = document.getElementById("static-route-reload");
    const sitesContainer = document.getElementById("static-route-sites-container");
    const ipRangesTableBody = document.querySelector(
        "#static-route-ipranges-table tbody"
    );

    function setStatus(message) {
        if (statusEl) {
            statusEl.textContent = message || "";
        }
    }

    function renderSites(sites) {
        if (!sitesContainer) return;

        sitesContainer.innerHTML = "";

        if (!sites || !sites.length) {
            const p = document.createElement("p");
            p.style.fontSize = "14px";
            p.style.color = "#666";
            p.textContent = "Site 情報が見つかりませんでした。";
            sitesContainer.appendChild(p);
            return;
        }

        sites.forEach((site) => {
            const details = document.createElement("details");
            details.className = "static-route-site-block";

            const summary = document.createElement("summary");
            summary.textContent = site.name || `Site (${site.id})`;
            summary.style.cursor = "pointer";
            summary.style.padding = "4px 0";
            summary.style.fontWeight = "600";

            details.appendChild(summary);

            const table = document.createElement("table");
            table.className = "table";
            table.innerHTML = `
                <thead>
                    <tr>
                        <th>Interface</th>
                        <th>Type</th>
                        <th>CIDR</th>
                        <th>Gateway</th>
                        <th>VLAN</th>
                        <th>DHCP</th>
                        <th>Name</th>
                    </tr>
                </thead>
                <tbody>
                    ${
                        (site.networks || [])
                            .map(
                                (n) => `
                        <tr>
                            <td>${n.interface_name || ""}</td>
                            <td>${n.type || ""}</td>
                            <td>${n.cidr || ""}</td>
                            <td>${n.gateway || ""}</td>
                            <td>${n.vlan ?? ""}</td>
                            <td>${n.dhcp_type || ""}</td>
                            <td>${n.subnet_name || ""}</td>
                        </tr>
                    `
                            )
                            .join("") ||
                        `<tr><td colspan="7">Network 情報がありません。</td></tr>`
                    }
                </tbody>
            `;

            details.appendChild(table);
            sitesContainer.appendChild(details);
        });
    }

    function renderIpRanges(ranges) {
        if (!ipRangesTableBody) return;

        ipRangesTableBody.innerHTML = "";

        const rows = [
            { label: "Default IP Range", key: "default" },
            { label: "Dynamic IP Range", key: "dynamic" },
            { label: "Static IP Range", key: "static" },
        ];

        rows.forEach((row) => {
            const tr = document.createElement("tr");
            const value = (ranges && ranges[row.key]) || "-";
            tr.innerHTML = `<td>${row.label}</td><td>${value}</td>`;
            ipRangesTableBody.appendChild(tr);
        });
    }

    async function fetchStaticRouteInit() {
        setStatus("データを取得しています...");
        if (sitesContainer) {
            sitesContainer.innerHTML =
                '<p style="font-size: 14px; color: #666;">データ取得中...</p>';
        }

        try {
            const res = await fetch("/api/network/static-route/init");
            if (res.status === 401) {
                setStatus("CMA にログインしてから利用してください。");
                if (sitesContainer) {
                    sitesContainer.innerHTML =
                        '<p style="font-size: 14px; color: #c00;">CMA にログインしてから利用してください。</p>';
                }
                return;
            }
            if (!res.ok) {
                setStatus("データ取得に失敗しました (HTTP " + res.status + ")。");
                return;
            }

            const json = await res.json();
            if (json.status !== "ok") {
                setStatus("データ取得に失敗しました: " + (json.message || "Unknown error"));
                return;
            }

            renderSites(json.sites || []);
            renderIpRanges(json.remoteIpRanges || {});
            setStatus("データ取得が完了しました。");
        } catch (e) {
            console.error("static route init error", e);
            setStatus("データ取得中にエラーが発生しました。");
        }
    }

    if (reloadBtn) {
        reloadBtn.addEventListener("click", (ev) => {
            ev.preventDefault();
            fetchStaticRouteInit();
        });
    }

    // ページ表示時に一度実行
    fetchStaticRouteInit();
});
