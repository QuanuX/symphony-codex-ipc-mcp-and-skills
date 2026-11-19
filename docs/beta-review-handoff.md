# GitHub and OpenAI beta review handoff

## Current handoff — November 19, 2026

Symphony `0.2.0-beta.2` is published. The [current package refresh](openai-beta2-refresh.md)
uses the released beta's client source, 523 native command contracts and 744
exposed tools. Prepare one package per exact released cohort with its matching
bridge, catalogue and provenance. The released bridge's `0.2.0-alpha.1` runtime
identity is separate from the beta.2 framework and refreshed package version.

Use the [beta.2 installation guide](https://downloads.quanux.org/symphony/0.2.0-beta.2/docs/BETA-INSTALL.md)
for verified downloads, fresh private installation and retention. The four
released profiles are macOS 15 ARM64, Ubuntu 24.04 AMD64, Ubuntu 24.04 ARM64 and
Ubuntu 26.04 AMD64. Preserve each cohort's qualification boundary.

Package alignment, OpenAI eligibility/review routing, portal validation and
publication are separate outcomes. Keep the earlier uploaded draft and its
checks as historical evidence. Do not describe new ZIPs as uploaded or approved
before those actions are verified. Keep the existing published MCPB and
`server.json` intact until an independently qualified replacement exists.

## Historical handoff — November 6, 2026

The following snapshot records the pre-launch plan and earlier draft. Its
future-tense delivery dates are historical commitments, not current availability
statements.

Publisher direction at that time: Symphony Beta was planned for **November 16,
2026**, with coordinated approval sought for that date. The schedule did not
guarantee reviewer approval.

This is the November 6 review snapshot. W13 advances the local source candidate
to 743 operation tools plus connection inspection (744 total), covering 523 of
525 native records. The earlier uploaded draft below remains a separate artifact;
its reported checks do not qualify W13. See [current compatibility](beta-compatibility.md).

### Available for review at that snapshot

- Symphony is publicly available, free open-source software under GNU AGPLv3: https://github.com/QuanuX/Symphony. There are no commercial feature gates or paid feature tiers. Normal native authorization and third-party service prerequisites remain applicable.
- Documentation: https://docs.quanux.org/symphony; administrative CLI: https://docs.quanux.org/symphony/qxctl/overview; existing getting-started guidance: https://docs.quanux.org/symphony/quickstart.
- The shared 0.2.0-line review specification is exactly `0.2.0-alpha.1`, matching the uploaded OpenAI draft. It exposes 265 read tools, 194 preview tools and 194 apply tools, plus connection inspection: 653 operation tools, 654 total, covering 459 native command contracts. Local C++/stdio and optional same-user IPC are retained.
- The next MCPB packaging specification includes the same catalogue and explicitly supplies `--tool-catalog`. Packaging reads the version from the plugin manifest rather than maintaining a separate hard-coded version.
- OpenAI draft checks were reported passed by the publisher. That does not establish local-MCP allowlisting or approval. Remaining metadata/native-help and new-interface demo requirements are disclosed in `public-operation-tools.md`.

### Planned delivery before November 16

1. Finalize official Symphony/qxctl installation channels and distribution URLs, including supported platforms and installation prerequisites.
2. Build and qualify the release binaries from the selected source revision. Build the MCPB from those binaries, preserving provenance; do not reuse an older executable under the new version.
3. Supply a short, tested end-user quick start based on the published MCPB: exact download/checksum, qxctl setup, private profile creation, client installation and expected read-only verification output.
4. Generate the new `server.json` from the actual MCPB URL/hash; verify all advertised versions and publish the corresponding registry update. Send GitHub the final bundle, metadata and quick-start links together. If the final version changes from `0.2.0-alpha.1`, update OpenAI's package to the same selected specification.

The existing root `server.json` and released MCPB still describe `0.1.0-alpha.1`. They remain accurate historical distribution records until the new release exists. Source-specification alignment is prepared; published-version alignment is explicitly pending. No provisional final URL or checksum is presented as real.

Request GitHub review the product explanation, public availability, license and shared interface now, and identify any further requirements now so the final next-week packet can receive prompt consideration for November 16. This is a request for a coordinated review timeline, not an assertion that approval has been granted.
