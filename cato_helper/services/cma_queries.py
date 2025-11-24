# cato_helper/services/cma_queries.py
from __future__ import annotations

# CMA の GraphQL クエリ定義をまとめるモジュール。
# 追加のクエリはこのファイルに増やしていく想定。

LOGIN_STATE_QUERY = (
    "query loginState($authcode: String, $authstate: String) {\n"
    "  loginState(authcode: $authcode, authstate: $authstate) {\n"
    "    id\n"
    "    firstName\n"
    "    lastName\n"
    "    email\n"
    "    role\n"
    "    appliedRole\n"
    "    elevatedForAll\n"
    "    elevatedAccountIds\n"
    "    accountType\n"
    "    username\n"
    "    personName\n"
    "    accountID\n"
    "    authService\n"
    "    accountName\n"
    "    preferredUi\n"
    "    presentUsageAndEvents\n"
    "    touIsApproved\n"
    "    whiteLabel {\n"
    "      key\n"
    "      theme\n"
    "      __typename\n"
    "    }\n"
    "    tags\n"
    "    adminTags\n"
    "    __typename\n"
    "  }\n"
    "}\n"
)
