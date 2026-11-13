[![M8ven Score](https://m8ven.ai/badge/mcp/quanux-symphony-codex-ipc-mcp-and-skills-176dh3)](https://m8ven.ai/mcp/quanux-symphony-codex-ipc-mcp-and-skills-176dh3?s=readme)

# Symphony Codex IPC/MCP and Skills

Standalone repository: [QuanuX/symphony-codex-ipc-mpc-and-skills](https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills). The implemented protocol is **MCP (Model Context Protocol)**; historical migration records preserve the former repository spelling. Runtime review-candidate version: `0.2.0-alpha.1`.

A C++26 MCP bridge, Codex skill/plugin, and reusable client adapters for direct administration of a selected Symphony installation. Publisher: **QuanuX**, [quanux.org](https://quanux.org).

This is a separately maintained integration, not a Symphony module. It builds without a Symphony source checkout and connects to an explicitly selected, independently installed `qxctl`. [Migration provenance](docs/repository-migration.md) identifies the original source and historical test evidence.

The public package exposes versioned, individually named operation tools and checks their contracts against the selected qxctl registry. It runs reads and previews/applies configured administration operations. It preserves qxctl as Symphony's operating interface and the native owners' identity, authority, receipts, versions and recovery rules. It adds no new vector or mandatory workload dependency. User modules and compositions remain open-ended.

This is a local Alpha candidate, not an OpenAI-approved directory release. Current compatibility is the explicitly pinned MCP **2025-11-25** protocol. See [verification](docs/verification.md), [host compatibility](docs/host-compatibility.md) and [public submission requirements](docs/submission.md).

## What Symphony and qxctl do

[Symphony](https://github.com/QuanuX/Symphony) is QuanuX's publicly available, free and open-source **quantOS** for composing quantitative research, trading systems and infrastructure. It is headless and self-hosted: users operate their own installations through agents and command-line tools. Symphony is licensed **GNU AGPLv3**, with no commercial feature gates or paid feature tiers. Native permissions, explicit authorization and third-party service requirements are operational controls, not paid access gates.

**qxctl** is Symphony's administrative command-line interface. It discovers installed capabilities and invokes their native owners using structured command contracts. This MCP bridge translates individually named agent tools into those qxctl operations; it does not install Symphony or replace the underlying engines.

- [Symphony documentation](https://docs.quanux.org/symphony)
- [qxctl documentation tab and overview](https://docs.quanux.org/symphony/qxctl/overview)
- [Current Symphony getting-started guidance](https://docs.quanux.org/symphony/quickstart)
- [Public Symphony source and license](https://github.com/QuanuX/Symphony)

The current public documentation/source are available now. Final beta installation channels, qxctl distribution URLs and the release-specific bundle quick start will be supplied in the release packet next week, before **November 16, 2026**. We are seeking coordinated approval for that beta date, not earlier publication.

## End-user bundle installation

The forthcoming 0.2.0 release packet will lead with a short, tested `.mcpb` installation path:

1. Install Symphony and its compatible qxctl using the finalized beta installation guide.
2. Download the matching published `.mcpb` and verify the release checksum.
3. Create a private connection profile selecting your qxctl installation, then install the bundle in a client that supports native MCP bundles and select that profile.
4. Ask the agent to inspect `symphony_connection`, then perform the documented harmless read. Enable only the non-read operations you intend to delegate.

This is the onboarding outline, not a claim that the beta download is published. The final packet will contain exact URLs, platform requirements, commands and expected results. Existing Alpha users can consult the [currently published 0.1.0-alpha.1 bundle](https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills/releases/tag/v0.1.0-alpha.1-mcpb) and [its setup instructions](docs/mcp-registry.md); that older bundle does not provide the 0.2.0 public operation catalogue.

## Shared 0.2.0 review specification

The exact current review version is **0.2.0-alpha.1**, in the 0.2.0 release line. Both the OpenAI ZIP and the next MCPB specification use the same local C++/stdio runtime and packaged catalogue: **743 operation tools plus connection status, 744 tools total**. The next MCPB manifest now selects that catalogue explicitly. See [W13 compatibility](docs/beta-compatibility.md) and the [dated beta review handoff](docs/beta-review-handoff.md). This source candidate does not replace or requalify previously uploaded packages.

`server.json` remains the truthful, checksum-pinned record of the already published **0.1.0-alpha.1** MCPB. It will be replaced by the generated 0.2.0 metadata only after the finalized new bundle exists. An old binary is never relabeled as 0.2.0. The source specification is aligned today; published-artifact and registry version alignment remain part of the later distribution packet.

## Developer build and connect

Requirements: macOS or Linux; a compiler accepting C++26 draft mode (`-std=c++2c`), CMake 3.30+, and Python 3.11+ for configuration/tests. Linux also requires OpenSSL 3 development files. nlohmann/json 3.12.0 is included with its license. No build-time dependency download occurs.

```sh
git clone https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills.git
cd symphony-codex-ipc-mcp-and-skills
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j 4
ctest --test-dir build --output-on-failure
cmake --install build --prefix "$PWD"
```

After building the binary into `bin/`, register this checkout's bundled marketplace with `codex plugin marketplace add "$PWD"`. In Codex Plugins, open **Personal → QuanuX — Symphony Codex IPC/MPC and Skills**, install Symphony, and use its setup skill to select your `qxctl`. The repository is source code; cloning alone does not provide a platform executable. Existing installed demo packages remain pinned copies and are not replaced by this repository move.

Select a registry-capable qxctl installation and an existing working directory explicitly (use a Symphony repository for repository-inspection commands):

```sh
python3 scripts/configure_connection.py \
  --qxctl /absolute/installation/bin/qxctl \
  --working-directory /absolute/Symphony \
  --output /absolute/private/connection.json

python3 scripts/configure_clients.py --client codex \
  --binary /absolute/plugin/bin/symphony-mcp \
  --config /absolute/private/connection.json \
  --tool-catalog /absolute/plugin/catalog/tools.json
```

The second command prints a client configuration fragment; review and add it to the intended host configuration. Use `--client claude`, `antigravity`, or `generic` for other MCP clients. These commands neither install into the host nor overwrite existing configuration. Full plugin installations instead read their connection profile from the host's documented plugin-data directory; see [host configuration](docs/host-compatibility.md).

Profiles default to read operations. Add `--enable EXACT_COMMAND_ID` when creating a profile to expose the specific non-read operations delegated to the agent. [Connection profiles](docs/connection-profile.md) describe pinning, environment forwarding, limits and replacement. Native authority still applies. An existing older qxctl without `commands manifest --json` is explicitly rejected; the adapter never upgrades it automatically.

## Agent interface

The public review candidate exposes **744 tools**: connection inspection and
743 individually defined read/preview/apply tools covering 523 native command
contracts. See the [catalogue and review boundaries](docs/public-operation-tools.md).
Each has named parameters, a description, input/output schemas and explicit safety
annotations. Clients page MCP `tools/list`; generic executors are not callable in
this mode. New installed commands require an explicit catalogue/package update.

Examples: `symphony_sov_remote_template`, `symphony_sov_target_inspect`,
`symphony_sov_target_configure_preview`, `symphony_sov_target_configure_apply`.
A preview can be applied only through its matching operation in the same session.
The [skill](skills/symphony-admin/SKILL.md) preserves native owner authority and
recovery. A listed tool does not establish native availability or service health.

The independent standalone mode without `--tool-catalog` retains the historical
registry/generic interface. It is not the public package's configured interface.
This change does not update the separately released MCP Registry bundle or the
standalone Notion repository.

A transport preview is not a native owner plan. Native expected-state checks and durable operation IDs remain essential for their applicable operations. Output is bounded and preserves exit code/stdout/stderr; it never equates process exit 0 with semantic success. A timeout, lost response or output limit during mutation requires owner observation/reconciliation before another action.

## Optional local IPC

The ordinary MCP stdio transport is already local IPC. An explicitly started same-user Unix-socket front end is also supplied:

```sh
mkdir -m 700 /absolute/private/symphony-ipc
bin/symphony-mcp --config /absolute/private/connection.json \
  --tool-catalog /absolute/plugin/catalog/tools.json \
  --listen /absolute/private/symphony-ipc/bridge.sock
```

In another process, launch `bin/symphony-mcp --connect-socket /absolute/private/symphony-ipc/bridge.sock` as the host's stdio server, or generate that adapter with `configure_clients.py --connect-socket ...`.

Both peers verify the kernel UID; the socket is 0600 in an owned 0700 directory. The bridge does not install a service automatically. It serves one local session at a time, with a 60-second idle limit. This is the bridge's transport, separate from qxctl's existing SSIAG/STAV transports. Windows named pipes, cross-user delegation, and a hosted HTTPS MCP endpoint are future adapters. See [security](docs/security.md) and [data handling](docs/privacy.md).

## Packaging and release

The native MCP Bundle (`.mcpb`) distribution packages the same C++ runtime for macOS Intel/Apple Silicon and Linux x86-64/ARM64. It requires an existing private connection profile and does not download, compile, upgrade or configure Symphony at launch. See [MCP Registry installation and publishing](docs/mcp-registry.md) for requirements, exact-package checks, and the separate official-registry/GitHub-catalogue publication steps. Windows hosts continue to use the explicit WSL adapter.

```sh
python3 scripts/package_release.py --binary build/symphony-mcp \
  --output /absolute/output/symphony-alpha-platform.zip
```

The packager includes source, the selected binary, skill, adapters and licenses; it excludes local profiles, build caches and private evidence. It emits an archive digest and never uploads. Build distinct qualified platform artifacts. A source-only archive omits `--binary` and requires a build before installation.

OpenAI's public local-MCP path currently requires partner allowlisting. Publisher contact, original branding, published plugin privacy coverage and [publisher-approved terms](https://quanux.org/symphony-plugin-terms) are included. The publisher supplied a demonstration, and an OpenAI draft was uploaded on 31 October 2026. Formal OpenAI review still requires local-MCP eligibility and completed per-operation metadata review; this independent MCP Registry distribution does not imply OpenAI approval. The configured C++ runtime and adapters have the focused evidence recorded in [Codex acceptance](docs/codex-acceptance.md). Neither this package nor a successful test guarantees a public launch date.

Eleven hosted plugin candidates now pass the [platform qualification checks](docs/platforms.md): Ubuntu on x86-64/ARM64, Apple Silicon and Windows-to-WSL 2. [Windows clients use an explicit WSL adapter](docs/windows-wsl2.md). DGX/Spark hardware and actual agent UI/native-owner acceptance remain open. The original verification report remains a dated baseline.

The manifest now offers the packaged `symphony-setup` onboarding workflow for selecting an existing installation and creating its private pinned profile. See [Codex acceptance](docs/codex-acceptance.md) for installed client evidence and remaining GUI checks. NVIDIA DGX/Spark qualification is a later milestone.
