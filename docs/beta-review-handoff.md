# GitHub and OpenAI beta review handoff

Publisher direction, November 6, 2026: Symphony Beta is planned for **November 16, 2026**. Seek coordinated approval for that date, not earlier publication. Reviewer approval is not guaranteed by this schedule.

This is the November 6 review snapshot. W13 advances the local source candidate
to 743 operation tools plus connection inspection (744 total), covering 523 of
525 native records. The earlier uploaded draft below remains a separate artifact;
its reported checks do not qualify W13. See [current compatibility](beta-compatibility.md).

## Available for review at that snapshot

- Symphony is publicly available, free open-source software under GNU AGPLv3: https://github.com/QuanuX/Symphony. There are no commercial feature gates or paid feature tiers. Normal native authorization and third-party service prerequisites remain applicable.
- Documentation: https://docs.quanux.org/symphony; administrative CLI: https://docs.quanux.org/symphony/qxctl/overview; existing getting-started guidance: https://docs.quanux.org/symphony/quickstart.
- The shared 0.2.0-line review specification is exactly `0.2.0-alpha.1`, matching the uploaded OpenAI draft. It exposes 265 read tools, 194 preview tools and 194 apply tools, plus connection inspection: 653 operation tools, 654 total, covering 459 native command contracts. Local C++/stdio and optional same-user IPC are retained.
- The next MCPB packaging specification includes the same catalogue and explicitly supplies `--tool-catalog`. Packaging reads the version from the plugin manifest rather than maintaining a separate hard-coded version.
- OpenAI draft checks were reported passed by the publisher. That does not establish local-MCP allowlisting or approval. Remaining metadata/native-help and new-interface demo requirements are disclosed in `public-operation-tools.md`.

## Final delivery next week, before November 16

1. Finalize official Symphony/qxctl installation channels and distribution URLs, including supported platforms and installation prerequisites.
2. Build and qualify the release binaries from the selected source revision. Build the MCPB from those binaries, preserving provenance; do not reuse an older executable under the new version.
3. Supply a short, tested end-user quick start based on the published MCPB: exact download/checksum, qxctl setup, private profile creation, client installation and expected read-only verification output.
4. Generate the new `server.json` from the actual MCPB URL/hash; verify all advertised versions and publish the corresponding registry update. Send GitHub the final bundle, metadata and quick-start links together. If the final version changes from `0.2.0-alpha.1`, update OpenAI's package to the same selected specification.

The existing root `server.json` and released MCPB still describe `0.1.0-alpha.1`. They remain accurate historical distribution records until the new release exists. Source-specification alignment is prepared; published-version alignment is explicitly pending. No provisional final URL or checksum is presented as real.

Request GitHub review the product explanation, public availability, license and shared interface now, and identify any further requirements now so the final next-week packet can receive prompt consideration for November 16. This is a request for a coordinated review timeline, not an assertion that approval has been granted.
