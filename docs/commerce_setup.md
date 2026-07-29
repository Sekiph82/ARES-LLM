# Shopify And Etsy Setup For Ares

Ares has a read-only commerce connector for Shopify and Etsy. It checks
connection status and fetches shop snapshots that can be saved into Ares memory.

No secrets are stored in the repository. Configure credentials as environment
variables before launching Ares.

## Shopify

Set:

```powershell
$env:ARES_SHOPIFY_SHOP = "your-shop.myshopify.com"
$env:ARES_SHOPIFY_ADMIN_TOKEN = "your-admin-api-token"
$env:ARES_SHOPIFY_API_VERSION = "2026-07"
```

Ares uses Shopify's Admin GraphQL API. Shopify requires a valid access token in
the `X-Shopify-Access-Token` header for Admin API requests. Shopify's REST Admin
API is legacy for new public apps, so Ares starts with GraphQL.

## Etsy

Set:

```powershell
$env:ARES_ETSY_API_KEY = "keystring:shared_secret"
$env:ARES_ETSY_ACCESS_TOKEN = "oauth-access-token"
$env:ARES_ETSY_SHOP_ID = "your-shop-id"
```

Etsy Open API v3 requires an API key on every request. OAuth is required for
private shop data and write operations.

## Safety

Current Ares commerce support is read-only. Write actions such as changing
inventory, updating prices, publishing listings, or handling orders should be
added only with:

- preview
- explicit approval
- audit log
- rollback or backup strategy where possible
