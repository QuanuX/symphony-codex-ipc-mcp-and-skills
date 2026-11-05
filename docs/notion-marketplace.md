# Notion listing preparation — draft, not submitted

Publisher: **QuanuX** · Website: https://quanux.org · Source:
https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills

Proposed listing name: **Symphony for Notion**

Short description: Connect Notion agents to your self-hosted Symphony quantOS,
and publish selected research, reports and incident records to your workspace.

Description draft: Symphony's optional adapter connects an authenticated Notion
agent to an installation you select. Discover available operations, inspect
results and perform authorized administration through qxctl and native Symphony
owners. A separate Notion OAuth connection publishes explicitly reviewed content
to allowed workspace pages. Symphony remains headless and user-hosted. Remote
tool calls and published content pass through Notion; permissions, infrastructure
and available operations depend on your installation and workspace.

## Required before claiming availability

- Real Notion Desktop/Agent testing over verified HTTPS, including header auth,
  protocol negotiation, scoped reads, authorized disposable writes and recovery.
- Public OAuth connection created with **Any workspace** scope, correct publisher
  identity, registered redirect and reviewed capabilities. Installation scope
  cannot be changed later. The operator-managed helper is implemented; a shared
  QuanuX OAuth secret must never be shipped to end users. Select and qualify a
  publisher-hosted onboarding backend if offering centralized public onboarding.
- Live OAuth consent, refresh, revoke and publication into a disposable permitted
  page; fixture evidence is not a Notion production receipt.
- Review the published privacy notice (https://quanux.org/privacy) and terms
  (https://quanux.org/symphony-plugin-terms) for Notion/proxy data flows, credentials,
  hosting, retention and revocation. Do not assume prior local-only review covers
  this optional remote path. Publisher approval precedes legal publication.
- Capture actual Notion screenshots and a short demo; use existing QuanuX assets
  only where their license/branding is appropriate. Do not create mock screenshots
  that imply a live connection has passed testing.
- Submit the listing separately in the Notion developer portal after those gates.

Custom MCP server setup and the API public-connection marketplace are separate
distribution paths. This packet establishes neither listing eligibility nor
Notion endorsement. No OpenAI submission or MCP Registry metadata is changed.

[Notion marketplace requirements](https://developers.notion.com/guides/connections-and-tokens/public-integrations/marketplace-listing)
and [public connections](https://developers.notion.com/guides/connections-and-tokens/public-integrations/overview), inspected 2026-11-04.
