from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


SHOPIFY_API_VERSION = "2026-07"
ETSY_API_BASE = "https://openapi.etsy.com/v3/application"


@dataclass(frozen=True)
class CommerceCheck:
    platform: str
    configured: bool
    ok: bool
    message: str
    data: dict[str, Any] | None = None


class CommerceError(RuntimeError):
    pass


class ShopifyClient:
    def __init__(self, shop: str, access_token: str, api_version: str = SHOPIFY_API_VERSION) -> None:
        self.shop = normalize_shop_domain(shop)
        self.access_token = access_token
        self.api_version = api_version

    @classmethod
    def from_env(cls) -> "ShopifyClient | None":
        shop = os.getenv("ARES_SHOPIFY_SHOP", "").strip()
        token = os.getenv("ARES_SHOPIFY_ADMIN_TOKEN", "").strip()
        version = os.getenv("ARES_SHOPIFY_API_VERSION", SHOPIFY_API_VERSION).strip() or SHOPIFY_API_VERSION
        if not shop or not token:
            return None
        return cls(shop=shop, access_token=token, api_version=version)

    @property
    def graphql_url(self) -> str:
        return f"https://{self.shop}/admin/api/{self.api_version}/graphql.json"

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
        request = urllib.request.Request(
            self.graphql_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": self.access_token,
            },
            method="POST",
        )
        return request_json(request)

    def summary(self) -> dict[str, Any]:
        query = """
        query AresShopSummary {
          shop {
            name
            myshopifyDomain
            currencyCode
            plan { displayName }
          }
          products(first: 5, sortKey: UPDATED_AT, reverse: true) {
            nodes {
              id
              title
              status
              totalInventory
              updatedAt
            }
          }
          orders(first: 5, sortKey: CREATED_AT, reverse: true) {
            nodes {
              id
              name
              displayFinancialStatus
              displayFulfillmentStatus
              createdAt
              totalPriceSet { shopMoney { amount currencyCode } }
            }
          }
        }
        """
        payload = self.graphql(query)
        if "errors" in payload:
            raise CommerceError(json.dumps(payload["errors"], indent=2))
        return payload.get("data", {})


class EtsyClient:
    def __init__(
        self,
        api_key: str,
        access_token: str | None = None,
        shop_id: str | None = None,
        api_base: str = ETSY_API_BASE,
    ) -> None:
        self.api_key = api_key
        self.access_token = access_token
        self.shop_id = shop_id
        self.api_base = api_base.rstrip("/")

    @classmethod
    def from_env(cls) -> "EtsyClient | None":
        api_key = os.getenv("ARES_ETSY_API_KEY", "").strip()
        access_token = os.getenv("ARES_ETSY_ACCESS_TOKEN", "").strip() or None
        shop_id = os.getenv("ARES_ETSY_SHOP_ID", "").strip() or None
        if not api_key:
            return None
        return cls(api_key=api_key, access_token=access_token, shop_id=shop_id)

    def get(self, path: str, query: dict[str, str | int] | None = None) -> dict[str, Any]:
        url = f"{self.api_base}/{path.lstrip('/')}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {"x-api-key": self.api_key}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return request_json(urllib.request.Request(url, headers=headers, method="GET"))

    def summary(self) -> dict[str, Any]:
        if not self.shop_id:
            raise CommerceError("ARES_ETSY_SHOP_ID is not configured.")
        shop = self.get(f"shops/{self.shop_id}")
        listings = self.get(f"shops/{self.shop_id}/listings/active", {"limit": 5})
        return {"shop": shop, "active_listings": listings}


def normalize_shop_domain(shop: str) -> str:
    shop = shop.removeprefix("https://").removeprefix("http://").strip("/")
    if "." not in shop:
        shop = f"{shop}.myshopify.com"
    return shop


def request_json(request: urllib.request.Request, timeout: int = 30) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise CommerceError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise CommerceError(str(exc.reason)) from exc


def check_commerce_connections() -> list[CommerceCheck]:
    checks: list[CommerceCheck] = []

    shopify = ShopifyClient.from_env()
    if shopify is None:
        checks.append(
            CommerceCheck(
                platform="Shopify",
                configured=False,
                ok=False,
                message="Missing ARES_SHOPIFY_SHOP or ARES_SHOPIFY_ADMIN_TOKEN.",
            )
        )
    else:
        try:
            data = shopify.summary()
            checks.append(CommerceCheck("Shopify", True, True, "Connected.", data=data))
        except CommerceError as exc:
            checks.append(CommerceCheck("Shopify", True, False, str(exc)))

    etsy = EtsyClient.from_env()
    if etsy is None:
        checks.append(
            CommerceCheck(
                platform="Etsy",
                configured=False,
                ok=False,
                message="Missing ARES_ETSY_API_KEY.",
            )
        )
    else:
        try:
            data = etsy.summary()
            checks.append(CommerceCheck("Etsy", True, True, "Connected.", data=data))
        except CommerceError as exc:
            checks.append(CommerceCheck("Etsy", True, False, str(exc)))

    return checks


def format_commerce_checks(checks: list[CommerceCheck]) -> str:
    blocks: list[str] = []
    for check in checks:
        status = "OK" if check.ok else "Needs setup" if not check.configured else "Error"
        blocks.append(f"## {check.platform}: {status}\n{check.message}")
        if check.data:
            blocks.append(json.dumps(check.data, indent=2)[:6000])
    return "\n\n".join(blocks)
