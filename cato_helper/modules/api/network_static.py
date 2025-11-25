# cato_helper/modules/api/network_static.py
from __future__ import annotations

from typing import Any

from flask import jsonify

from . import bp
from ...services.cma_session import (
    has_cma_state,
    _build_requests_session_from_state,  # 内部ヘルパーだが、ここでは割り切って利用する
    CMA_GRAPHQL_URL,
)
from ...services.cma_queries import LOGIN_STATE_QUERY
from ...services.response_store import save_response


# --- GraphQL クエリ定義（必要な項目だけの軽量版） ---


ACCOUNT_SNAPSHOT_SITES_QUERY = """query accountSnapshotSites($accountID: ID!) {
  accountSnapshot(accountID: $accountID) {
    id
    sites {
      id
      info {
        name
      }
    }
  }
}
"""


SITE_INFO_QUERY = """query siteInfo($siteId: ID!) {
  siteInfo(id: $siteId) {
    id
    name
    interfaces {
      id
      name
      subnets {
        id
        name
        type
        subnet {
          id
        }
        gateway {
          id
        }
        vlanTag
        dhcpSettings {
          dhcpType
        }
      }
    }
  }
}
"""


ACCOUNT_IP_RANGES_QUERY = """query account($accountID: ID!) {
  account(accountID: $accountID) {
    id
    vpnRange {
      id
    }
    vpnRangeForDynamicIPAllocation {
      id
    }
    accessSettings {
      staticIpRange {
        id
      }
    }
  }
}
"""


def _post_graphql(
    sess, query: str, variables: dict[str, Any] | None, operation_name: str, save_name: str
) -> dict[str, Any]:
    """共通の GraphQL POST ヘルパー。

    - CMA の既存セッションを使って GraphQL を叩く
    - デバッグ用にレスポンスを response_store に保存する
    """
    payload: dict[str, Any] = {
        "operationName": operation_name,
        "variables": variables or {},
        "query": query,
    }

    resp = sess.post(CMA_GRAPHQL_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # 解析用に保存（失敗/成功に関わらず）
    try:
        save_response(save_name, data)
    except Exception:
        # 保存に失敗しても API 自体は継続する
        pass

    if not isinstance(data, dict) or "data" not in data:
        raise RuntimeError("Unexpected GraphQL response format")

    return data["data"]


@bp.route("/network/static-route/init", methods=["GET"])
def static_route_init() -> tuple[Any, int] | Any:
    """Static Route 追加画面の初期データを返す API。

    - Site 一覧 + 各 Site の Network 情報
    - SDP リモートユーザー用 IP Range（Default / Dynamic / Static）
    """  # noqa: D401
    if not has_cma_state():
        # CMA 未ログイン
        return jsonify({"status": "error", "message": "CMA not logged in"}), 401

    # Playwright で保存された state から requests.Session を構築
    try:
        sess = _build_requests_session_from_state()
    except Exception as e:  # noqa: BLE001
        return jsonify({"status": "error", "message": str(e)}), 500

    # --- 1) loginState から accountID を取得 ---
    try:
        login_data = _post_graphql(
            sess,
            LOGIN_STATE_QUERY,
            {"authcode": None, "authstate": None},
            "loginState",
            "loginState_for_static_route",
        )
        login_state = login_data.get("loginState", {}) if isinstance(login_data, dict) else {}
        account_id = login_state.get("accountID")
        if not account_id:
            raise RuntimeError("accountID not found in loginState response")
    except Exception as e:  # noqa: BLE001
        return jsonify({"status": "error", "message": f"loginState error: {e}"}), 500

    # --- 2) Site 一覧を取得 ---
    try:
        snapshot_data = _post_graphql(
            sess,
            ACCOUNT_SNAPSHOT_SITES_QUERY,
            {"accountID": str(account_id)},
            "accountSnapshotSites",
            "accountSnapshotSites_for_static_route",
        )
        snapshot = snapshot_data.get("accountSnapshot", {}) if isinstance(snapshot_data, dict) else {}
        raw_sites = snapshot.get("sites", []) or []
    except Exception as e:  # noqa: BLE001
        return jsonify({"status": "error", "message": f"accountSnapshotSites error: {e}"}), 500

    # --- 3) 各 Site ごとの Network 情報を取得 ---
    sites_with_networks: list[dict[str, Any]] = []

    for site in raw_sites:
        site_id = site.get("id")
        info = site.get("info", {}) or {}
        site_name = info.get("name") or f"Site {site_id}"

        if not site_id:
            # ID が取れない場合はスキップ
            continue

        try:
            site_info_data = _post_graphql(
                sess,
                SITE_INFO_QUERY,
                {"siteId": str(site_id)},
                "siteInfo",
                f"siteInfo_{site_id}",
            )
            site_info = site_info_data.get("siteInfo", {}) if isinstance(site_info_data, dict) else {}
        except Exception as e:  # noqa: BLE001
            # 1 Site だけ失敗しても他の Site は返す
            site_info = {"interfaces": []}
            site_name = f"{site_name} (取得エラー: {e})"

        networks: list[dict[str, Any]] = []
        for iface in site_info.get("interfaces", []) or []:
            iface_name = iface.get("name") or ""
            for subnet in iface.get("subnets", []) or []:
                subnet_obj = subnet.get("subnet") or {}
                gw_obj = subnet.get("gateway") or {}
                dhcp_settings = subnet.get("dhcpSettings") or {}

                networks.append(
                    {
                        "interface_name": iface_name,
                        "subnet_name": subnet.get("name"),
                        "type": subnet.get("type"),
                        "cidr": subnet_obj.get("id"),
                        "gateway": gw_obj.get("id"),
                        "vlan": subnet.get("vlanTag"),
                        "dhcp_type": dhcp_settings.get("dhcpType"),
                    }
                )

        sites_with_networks.append(
            {
                "id": site_id,
                "name": site_name,
                "networks": networks,
            }
        )

    # --- 4) アカウントの SDP IP Range を取得 ---
    try:
        account_data_root = _post_graphql(
            sess,
            ACCOUNT_IP_RANGES_QUERY,
            {"accountID": str(account_id)},
            "account",
            "account_for_static_route",
        )
        account_data = account_data_root.get("account", {}) if isinstance(account_data_root, dict) else {}
    except Exception as e:  # noqa: BLE001
        return jsonify({"status": "error", "message": f"account (IP ranges) error: {e}"}), 500

    vpn_range = account_data.get("vpnRange") or {}
    vpn_range_dyn = account_data.get("vpnRangeForDynamicIPAllocation") or {}
    access_settings = account_data.get("accessSettings") or {}
    static_ip_range = access_settings.get("staticIpRange") or {}

    remote_ip_ranges = {
        "default": vpn_range.get("id"),
        "dynamic": vpn_range_dyn.get("id"),
        "static": static_ip_range.get("id"),
    }

    return jsonify(
        {
            "status": "ok",
            "sites": sites_with_networks,
            "remoteIpRanges": remote_ip_ranges,
        }
    )
