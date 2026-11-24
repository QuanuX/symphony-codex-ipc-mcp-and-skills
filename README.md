[![M8ven Score](https://m8ven.ai/badge/mcp/quanux-symphony-codex-ipc-mcp-and-skills-176dh3)](https://m8ven.ai/mcp/quanux-symphony-codex-ipc-mcp-and-skills-176dh3?s=readme)

# Symphony Codex IPC/MCP and Skills

Standalone repository: [QuanuX/symphony-codex-ipc-mcp-and-skills](https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills). The implemented protocol is **MCP (Model Context Protocol)**; historical migration records preserve the former repository spelling. This package refresh targets **Symphony `0.2.0-beta.2.1`**. The packaged bridge and plugin report `0.2.0-beta.2.1`. The matching signed framework supplies qxctl and the operation catalogue.

A C++26 MCP bridge, Codex skill/plugin, and reusable client adapters for direct administration of a selected Symphony installation. Publisher: **QuanuX**, [quanux.org](https://quanux.org).

This is a separately maintained integration, not a Symphony module. It builds without a Symphony source checkout and connects to an explicitly selected, independently installed `qxctl`. [Migration provenance](docs/repository-migration.md) identifies the original source and historical test evidence.

The public package exposes versioned, individually named operation tools and checks their contracts against the selected qxctl registry. It runs reads and previews/applies configured administration operations. It preserves qxctl as Symphony's operating interface and the native owners' identity, authority, receipts, versions and recovery rules. It adds no new vector or mandatory workload dependency. User modules and compositions remain open-ended.

This is a local integration for the public beta. OpenAI directory approval remains a separate review outcome. Current compatibility uses the explicitly pinned MCP **2025-11-25** protocol. See the [beta.2.1 package refresh](docs/openai-beta21-review.md), [verification](docs/verification.md), [host compatibility](docs/host-compatibility.md) and [submission history](docs/submission.md).

## What Symphony and qxctl do

[Symphony](https://github.com/QuanuX/Symphony) is QuanuX's publicly available, free and open-source **quantOS** for composing quantitative research, trading systems and infrastructure. It is headless and self-hosted: users operate their own installations through agents and command-line tools. Symphony is licensed **GNU AGPLv3**, with no commercial feature gates or paid feature tiers. Native permissions, explicit authorization and third-party service requirements are operational controls, not paid access gates.

**qxctl** is Symphony's administrative command-line interface. It discovers installed capabilities and invokes their native owners using structured command contracts. This MCP bridge translates individually named agent tools into those qxctl operations; it does not install Symphony or replace the underlying engines.

- [Symphony documentation](https://docs.quanux.org/symphony)
- [qxctl documentation tab and overview](https://docs.quanux.org/symphony/qxctl/overview)
- [Current Symphony getting-started guidance](https://docs.quanux.org/symphony/quickstart)
- [Public Symphony source and license](https://github.com/QuanuX/Symphony)
- [Published Symphony beta.2.1 release](https://github.com/QuanuX/symphony-distribution/releases/tag/v0.2.0-beta.2.1)
- [Beta.2.1 installation and retention guide](https://downloads.quanux.org/symphony/0.2.0-beta.2.1/docs/BETA-INSTALL.md)

Symphony beta.2.1 is published. Users design their own engines, strategies and integrations and operate them on their own clusters; supplied engines demonstrate capabilities. The agent bridge preserves the selected native contracts and user authority. It adds no QuanuX telemetry or remote support entry point.

## Install the Codex plugin

Start at [Symphony downloads](https://quanux.org/downloads#codex) to install the signed Symphony framework and the Codex plugin together. The plugin also works with a separately retained beta.2.1 `qxctl` on the same host. Use an ordinary user account with Python 3.11+, `curl` and a Codex CLI that supports `plugin marketplace add` and `plugin add`. For an existing installation, download the [Codex setup helper](https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills/releases/download/v0.2.0-beta.2.1/install-codex.py) and run it locally. The downloads page includes a checksum-verified command.

```sh
python3 -I install-codex.py
```

The default selection is `~/symphony-0.2.0-beta.2.1/bin/qxctl` with your home directory as the Symphony working directory. To select another copy of that release, run `python3 -I install-codex.py --qxctl /absolute/path/to/qxctl --working-directory /absolute/workspace`. Use `--codex-bin /absolute/path/to/codex` for a separately installed CLI. The `--archive /absolute/path/to/plugin.zip` option verifies a previously downloaded [profile ZIP](https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills/releases/tag/v0.2.0-beta.2.1).

The helper selects and verifies the platform ZIP, registers the QuanuX Symphony local marketplace, installs both skills and the native MCP server, and pins the selected `qxctl` in the plugin’s private read-only connection. The local installation is available independently of OpenAI directory approval. Existing workspace plugin permissions still apply.

Open a **new Codex chat** and ask “Use `symphony_connection` to report the bridge version, then read the SOV target configuration template.” Expect `0.2.0-beta.2.1` and a native `symphony.sov.remote-template.v1` result. The catalogue contains 744 tools. Adding a profile with write permissions is a separate operator action.

| Release profile | Plugin evidence |
| --- | --- |
| Ubuntu 26.04 AMD64 | Fresh framework installation, installed Codex plugin and native read in an Ubuntu container on an Intel Mac. |
| Ubuntu 24.04 AMD64 | Rebuilt server executed the native fixture suites in an Ubuntu container. |
| macOS 15 ARM64 | Apple Silicon cross-build with minimum deployment target 15.0. Runtime execution on Apple Silicon is pending. |
| Ubuntu 24.04 ARM64 | Candidate tested with real ARM64 qxctl under emulation. The original two fixture deadline failures and supplemental passing tests are detailed in the [build record](packaging/beta21/bridge-builds.json). |

For signed framework downloads and manual retention, use the [release installation guide](https://github.com/QuanuX/symphony-distribution/releases/download/v0.2.0-beta.2.1/BETA-INSTALL.md). The macOS framework package uses a detached publisher signature. For help, visit [QuanuX support](https://support.quanux.org).

## Beta.2.1 review interface and provenance

The refreshed interface contains **303 read tools, 220 preview tools and 220 apply tools**, plus `symphony_connection`: **744 tools total**, covering **523 native command contracts**. It incorporates the client source used by the released beta, including catalogue and compatibility verification. Local C++/stdio and optional same-user IPC remain the transports. See the [beta.2.1 refresh record](docs/openai-beta21-review.md), [W13 compatibility](docs/beta-compatibility.md) and [dated review handoff](docs/beta-review-handoff.md).

Each selected package records its exact bridge, qxctl and catalogue binding in root `package-profile.json` (`symphony.beta-review-package.v2`). Read that receipt before setup. A shared tool count does not make executable hashes or observed-registry digests interchangeable. The receipt identifies the new bridge build and the framework’s original client separately. The retained framework client still identifies itself as `0.2.0-alpha.1`. Launch `bin/symphony-mcp` from the selected plugin ZIP.

`server.json` remains the checksum-pinned record of the published **0.1.0-alpha.1** MCPB until a verified replacement bundle exists. Profile-specific OpenAI ZIPs do not replace that registry artifact or establish OpenAI submission, eligibility or approval.

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

Prepare beta.2.1 review ZIPs for the exact released cohorts above. Include each cohort's matching bridge and catalogue, the updated skills, corresponding source, licenses and provenance. Follow the [beta.2.1 refresh record](docs/openai-beta21-review.md) for the packaging boundary. Neither package extraction nor client launch installs or activates Symphony services.

The existing native MCPB packaging path targets macOS Intel/Apple Silicon and Linux x86-64/ARM64. Its target model is broader than the published beta.2.1 cohort set and does not distinguish Ubuntu 24.04 from 26.04 AMD64. Qualify a replacement explicitly before changing the published bundle or `server.json`. [MCP Registry installation and publishing](docs/mcp-registry.md) records that separate channel. The Windows-to-WSL adapter remains available; its historical checks do not add a beta.2.1 Windows qualification.

The beta.2.1 packager includes committed source, the newly built bridge and the signed release catalogue, both skills, adapters, licenses and profile provenance. It excludes local profiles, build caches and private evidence, emits an archive digest and never uploads. Use the [reproduction commands](docs/openai-beta21-review.md#reproduce-the-review-package) for a verified profile package. The separate generic `scripts/package_release.py` can create a developer source archive by omitting `--binary`; that archive requires a build before installation and does not establish beta.2.1 profile qualification.

Publisher contact, original branding, published plugin privacy coverage and [publisher-approved terms](https://quanux.org/symphony-plugin-terms) are included. The earlier submitted draft and demonstration remain dated review artifacts. The beta.2.1 refresh addresses package compatibility; confirm local-MCP eligibility, review routing and acceptance separately with OpenAI. The configured C++ runtime and adapters have the focused historical evidence recorded in [Codex acceptance](docs/codex-acceptance.md). A successful package test does not establish directory approval.

The [historical platform qualification record](docs/platforms.md) covers eleven earlier native/WSL candidates and separate clean-package checks. Apply those results only to their recorded bytes and environments. [Windows clients use an explicit WSL adapter](docs/windows-wsl2.md). DGX/Spark hardware and actual desktop GUI acceptance require their own evidence.

The manifest now offers the packaged `symphony-setup` onboarding workflow for selecting an existing installation and creating its private pinned profile. See [Codex acceptance](docs/codex-acceptance.md) for installed client evidence and remaining GUI checks. NVIDIA DGX/Spark qualification is a later milestone.

The [D08 stamped-owner handoff](docs/d08-stamped-owner-handoff.md) is retained as historical source-binding evidence. The beta.2.1 release uses its own exact native source and per-profile artifacts; current package evidence must bind those bytes.
