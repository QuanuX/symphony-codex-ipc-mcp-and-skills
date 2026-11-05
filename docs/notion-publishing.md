# Publish Symphony reports, incidents and research into Notion

This optional Python 3.11+ standard-library adapter implements Notion OAuth
authorization, explicit refresh/revocation, publication previews and one-attempt
page creation. It is independent of the C++ MCP gateway. It does not run Symphony
commands, synchronize arbitrary files, watch Notion pages or treat page edits as
execution instructions. API version is pinned to **2026-03-11**.

## Prepare a connection

Choose the destination workspace and parent pages. Create your own Notion OAuth
connection and grant only the required page/content capabilities. Register the
exact callback URI. A public connection uses **Any workspace** installation scope
if marketplace eligibility is intended. Actual consent determines accessible pages.

Copy `adapters/notion/publisher.json.example` to a private 0700 directory as
`publisher.json`, mode 0600. Replace every example selection. Store the OAuth
client secret in a separate 0600 JSON file containing `{"client_secret":"..."}`.
Never distribute QuanuX's shared OAuth client secret in a desktop package. This
operator-managed adapter expects a registration the operator controls. A centrally
managed QuanuX onboarding service would need a publisher-hosted confidential
OAuth backend and its own deployment/security qualification before public launch.

The callback listener binds 127.0.0.1. An HTTPS registered callback must route
`/notion/callback` to loopback port 8766 using operator-owned infrastructure.
Loopback HTTP is also supported in the helper, subject to Notion accepting that
registered redirect URI. The state expires after ten minutes and is single-use;
URLs/codes are not logged. A mismatched workspace is rejected. If consent created
a grant for the wrong workspace, remove it through Notion's connection settings.

```sh
python3 scripts/notion_publish.py --config /absolute/private/publisher.json authorize
python3 scripts/notion_publish.py --config /absolute/private/publisher.json status
```

Complete consent in your browser; do not give the agent passwords or paste tokens
in chat. `status` reports stored identity and destinations; it does not probe live
Notion access. The protected token file retains access/refresh tokens and the
workspace identity returned by Notion.

## Preview, approve and publish

Prepare a report from explicit content selected for external disclosure:

```sh
python3 scripts/notion_publish.py --config /absolute/private/publisher.json prepare \
  --kind research --parent-page YOUR_ALLOWED_PAGE_ID --title 'Research result' \
  --body-file /absolute/private/report.txt --output /absolute/private/report-plan.json
```

`--kind` accepts `report`, `incident` or `research`. Inspect the plan's exact
payload, workspace, parent page and checksum. It creates plain-text paragraphs
with a unique publication ID; Markdown is preserved as text, not interpreted.
Titles and body lengths are bounded and split into supported rich-text blocks.
It creates a child page, not a database/data-source row or an existing-page edit.

When the user's task authorizes sending that content to that destination:

```sh
python3 scripts/notion_publish.py --config /absolute/private/publisher.json publish \
  --plan /absolute/private/report-plan.json --approve-sha256 SHA_FROM_PREVIEW
```

Plans expire after 15 minutes and bind the exact payload and token/workspace.
The checksum is an integrity/selection check, not a native authority grant or a
substitute for user authorization. The same-OS-user trust boundary applies.

A private `.receipt.json` file is exclusively created and synced **before** the
network request. That plan cannot be sent again even after a crash or response
loss. A completed receipt includes Notion's page ID and URL. On uncertainty,
search Notion for the publication ID and inspect the receipt before preparing
another plan. The API does not promise exactly-once publication; this adapter
does not silently retry timeouts, rate limits, 5xx responses or redirects.

## Credential lifecycle

`refresh` rotates tokens explicitly and invalidates old publication previews.
An unresolved refresh leaves `.refresh-pending.json`, preventing another refresh
attempt. Reconcile or reauthorize instead of deleting this marker blindly.
`revoke` calls Notion's revocation endpoint and removes the local token after a
successful response. If a revocation response is lost, use Notion's connection
settings to confirm revocation before removing local credentials. Disconnecting
the MCP gateway is separate from revoking the Notion publishing connection.

The helper always uses verified HTTPS to api.notion.com, forbids redirects and
does not print response bodies or credentials. Files selected for publication
are sent to Notion and governed by the user's Notion workspace policies. Existing
QuanuX notices need review for this new optional path before marketplace launch.

Official contracts inspected 2026-11-04:
[OAuth](https://developers.notion.com/guides/authorization/overview),
[token](https://developers.notion.com/reference/create-a-token),
[refresh](https://developers.notion.com/reference/refresh-a-token),
[revocation](https://developers.notion.com/reference/revoke-token),
[page creation](https://developers.notion.com/reference/post-page).
