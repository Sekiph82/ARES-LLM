from local_llm.commerce import EtsyClient, ShopifyClient, normalize_shop_domain


def test_normalize_shop_domain() -> None:
    assert normalize_shop_domain("demo") == "demo.myshopify.com"
    assert normalize_shop_domain("https://demo.myshopify.com/") == "demo.myshopify.com"


def test_shopify_from_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("ARES_SHOPIFY_SHOP", raising=False)
    monkeypatch.delenv("ARES_SHOPIFY_ADMIN_TOKEN", raising=False)

    assert ShopifyClient.from_env() is None


def test_etsy_from_env(monkeypatch) -> None:
    monkeypatch.setenv("ARES_ETSY_API_KEY", "key:secret")
    monkeypatch.setenv("ARES_ETSY_SHOP_ID", "123")

    client = EtsyClient.from_env()

    assert client is not None
    assert client.shop_id == "123"
