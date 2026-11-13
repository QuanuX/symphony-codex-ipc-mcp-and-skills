# W13 engineering handoff — 13 November 2026

W13 implementation and local qualification are complete for the source pair below.
Hosted PR/platform checks and human review remain pending; this record does not
accept or publish the Public Beta. The feature freeze remains in force.

## Qualified source and private artifact

- Symphony: `995cc46d11e509180f589d32ea859c3795a4a844`, tree
  `ffec92cedc5e169a5c21b82d5c4b246bf19eee54`, [core PR #198](https://github.com/QuanuX/Symphony/pull/198).
- Client: `62bfdd948025376aab94c031731cd4543a6850ac`, tree
  `48cf034c2a98684195447af86c011db55c7b1a97`, [client PR #6](https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills/pull/6), stacked on unmerged client #5.
- Private ZIP: `symphony-w13-macos-x86_64-final.zip`, 86 members, SHA256
  `351dff2ebfede7d85a3c85c57c2850e810e418af9aad085dba40926510330ef7`.
- Compatibility report SHA256:
  `538f5ba09993d1d4a78917ef39ccf10fe6443c8beb55f30f2b342fbdfd5b11d5`.
- Package inventory SHA256:
  `d9d01c5d2d08804bac4954a4dfb22b0c64f509ac5fb36a35142d4adfa6488925`.

Later handoff-only commits do not change these tested artifact identities. A new
package requires new bindings; neither the version label nor a later branch head
substitutes for the committed pair. Private evidence and configuration are retained
outside the repository; hashes above identify the review packet without publishing
machine paths. The packet's requirements remain subject to independent review.

## Implementation and acceptance mapping

| Increment | Result and evidence |
| --- | --- |
| W13.1 source pair | Exact source commits/trees, reproducible stamped qxctl, expected projection verified by qxctl, observed registry and package inventories retained. |
| W13.2 catalog | 525 native identities reconciled: 523 callable contracts, 743 operation tools plus connection status; 64 additions, five changed contracts, no removed native identities, two intentional exclusions. All 523 native help probes pass. |
| W13.3 admission/recovery | Exact records and read-only defaults retained. Public-tool regressions cover complete descriptor pagination, forbidden generic executors, disabled/drifted contracts, changed files, session/operation binding, native failure and single consumption. A real 301-second expiry check rejected the expired preview with zero dispatches. Oversized/deep requests also caused zero dispatches. |
| W13.4 adapters | Codex, Claude Code, Antigravity, generic stdio and explicit WSL adapters maintained. Eight adapter checks pass. WSL smoke now exercises both legacy and public interfaces. |
| W13.5 evidence | Bounded two-repository verifier/schema and ten negative/incomplete/integrity regressions pass. Actual packet: 27 hashed attachments, two modes, 22 cases; `engineering_review_ready`, with acceptance/publication false. Maps to C02.4 and MCP-CHANNELS. |
| W13.6 integration | All eight local CTest groups passed with no skips; 11 MCPB packaging checks passed. Exact staged package passed 22 Codex/native-owner cases. Affected-path PR CI is automatic; retained platform smoke is dispatched separately without waiting for results. |
| W13.7 handoff | Source/artifact identities, qualified scope, retained limits and distribution inputs are recorded here. Human acceptance and hosted results must be reviewed before merging/accepting the milestone. |

Core PR #198 repairs an existing dispatch guard that rejected the registered
Accordare families before their handlers. CLI/help/registry/contract tests and the
1,411-input source-map check passed. It introduces no native command or authority.
The six formerly unavailable help routes now reach existing owner validation.

The bridge implementation is unchanged. The local run exposed and corrected a
fixture readiness race between socket creation and chmod/listen completion; tests
and the Codex harness now wait for private permissions and successful connection.

The private ZIP reproduced byte-for-byte. Every source member was compared to the
selected plugin commit. qxctl reproduced across two isolated build/cache paths.
Local tools: Go 1.26.5, Clang 23.1.2, CMake 4.4.3, Python 3.14.5. macOS deployment
target 14.0 is a build setting, not proof of execution on macOS 14. The final
configuration-binding verifier change reran its ten tests and exact-package Codex
qualification; unchanged compiled sources/build rules retain the eight-group
milestone evidence, with that dependency comparison recorded explicitly.

## Client and platform matrix

| Client/target | Observed status | Limit |
| --- | --- | --- |
| Codex 0.167.0-alpha.4.1, macOS 26.7.1 x86-64, stdio | 11 actual app-server/native-owner cases passed | Deterministic calls, not model selection or GUI/plugin-store onboarding. |
| Same Codex/host, same-user IPC | 11 actual cases passed, including disconnect/reconnect | Serial local IPC; no concurrent cancellation, streaming, cross-user or network claim. |
| Claude Code, Antigravity, generic stdio | Configuration/quoting/privacy/refusal fixtures passed | Actual client sessions remain unqualified; Claude Desktop is not inferred. |
| Explicit Windows-to-WSL adapter | Configuration and smoke-validator fixtures passed | Actual Windows/WSL execution awaits the retained hosted lane. |
| Ubuntu 24.04 x86-64, macOS 15 ARM, Windows/Ubuntu 24.04 WSL2 | Existing smoke campaign retained | Results are not awaited or asserted here. Existing broader target rows remain in the manual campaign. |

The actual owner lifecycle created, inspected, updated and removed disposable SOV
configuration. Synthetic target/job references were never invoked. The lost reply
case observed durable owner state after restart and did not replay the write. Both
runs left no owner configuration behind. This does not qualify live Cloudflare,
Rithmic, SSIAG grants, Accordare installations, remote invocation or trading.

## Distribution work after W13

| Priority | Concrete next work | Owner/acceptance |
| --- | --- | --- |
| 1 | Review hosted checks and the source pair; integrate core #198 and client #5/#6 in dependency order. | Component maintainer; @quantDIY retains merge/scope decisions. |
| 2 | Select Anaconda account/channel, package form and intentional release version. Keep native and client packages/source identities distinct. | Publisher decision; no destination or upload is selected by W13. |
| 3 | Supply publisher signing identities, independently delivered trust policy, notices, loader/platform requirements and final artifact inventories. | Publisher plus independent trust reviewer; names/policy still pending. |
| 4 | Produce and retrieve final artifacts through the chosen channel, record real URLs/digests, and run fresh-host install/read/recovery/remove and rollback gates. | Channel and target-host owners; local private ZIP success is not this gate. |
| 5 | Complete independent acceptance and backup review; reconcile retained W08/W12/provider gaps against all core/paper/supplemental cells. | Named acceptance and backup reviewers still pending. |

Keep `server.json` at the real published 0.1.0-alpha.1 artifact until a replacement
exists. The unpublished candidate remains 0.2.0-alpha.1. Direct archives, MCPB/MCP
Registry, Anaconda and the OpenAI directory have separate distribution/approval
states. Neither the companion nor this handoff changes the native delivery
index's single-source rule or closes final-channel acceptance.
