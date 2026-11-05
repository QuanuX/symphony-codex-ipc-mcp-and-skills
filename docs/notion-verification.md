# Notion adapter development verification — 2026-11-04

Base repository revision: `89bc8f3b615ebc993183086e9cf7189a0d583c64`.
Local host: Intel macOS, AppleClang 21, C++26 mode. Gateway is opt-in;
the default local MCP entry and pending public review packages are unchanged.

## Passed locally

- Existing transport, bounded hashing, MCP integration and client-adapter CTest
  groups pass after the shared-core extraction. The extracted Bridge implementation
  is byte-for-byte identical to its previous source section; no domain behavior
  was changed during that refactor.
- **12 gateway cases** use real loopback HTTP, the C++ bridge and synthetic qxctl:
  authentication, Host/Origin/version checks, command/tool scope, metadata audit,
  session isolation, token rotation/revocation, ambiguous-token rejection, preview
  isolation, one-use apply, request-ID conflict/replay, deliberate HTTP response
  loss without repeated write, native refusal, expiry/capacity, malformed inputs,
  payload limits, duplicate Authorization headers, private-profile generation,
  existing same-UID IPC and IPC loss/session invalidation.
- The same 12 cases pass with AddressSanitizer and UndefinedBehaviorSanitizer.
- **11 Notion publishing cases** verify content previews, all document kinds,
  Unicode splitting, destination/expiry/checksum/token binding, durable one-attempt
  receipts, response-loss handling, refresh rotation/loss, revocation, private
  files, redirect refusal, bounded requests, exact API headers, and state/workspace
  checks on simulated OAuth callbacks. Notion API responses are fixtures.
- Skill validator, Python compilation, launchd plist syntax, whitespace checks,
  archive CRC, executable modes and exact tested binary bytes pass.

The restricted execution environment initially denied loopback/socket binds;
the affected tests were rerun with local-socket permission and passed. No real
Symphony installation, native grant or Notion workspace was modified.

The vendored HTTP server is cpp-httplib **v0.64.0**, with its upstream MIT license
and SHA-256 in `third_party/NOTICE.md`. The current upstream advisory list was
reviewed; this selection is newer than the published fixes for header decoding,
negative chunk sizes and GET-body request smuggling. This is not a comprehensive
security certification.

## Not established by these tests

Actual Notion Desktop/Agent handshake and permission UX; live Notion OAuth or page
creation; TLS/proxy/tunnel deployment; cross-host identity; hosted Ubuntu/Apple
Silicon CI results; WSL/DGX qualification of this new gateway; native signing;
publisher-hosted OAuth onboarding; policy approval; marketplace submission or
acceptance. The PR adds hosted Ubuntu/Apple Silicon test automation; its live
check results are authoritative for those lanes.

See [gateway acceptance](notion-integration.md), [publication recovery](notion-publishing.md)
and [marketplace requirements](notion-marketplace.md) for completing those checks.
