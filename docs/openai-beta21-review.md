# Symphony 0.2.0-beta.2.1 desktop plugin

The plugin bundles both Symphony skills, the C++ MCP server, its build source, and the release catalogue for one operating-system profile. The server reports `0.2.0-beta.2.1` through `--version`, the MCP `initialize` response and `symphony_connection`. The signed framework installer still contains the original client. Launch the server in the plugin ZIP when testing the updated integration.

## Install and connect

1. Use the [official beta.2.1 installer and verification instructions](https://github.com/QuanuX/symphony-distribution/releases/tag/v0.2.0-beta.2.1). Install into a new private prefix, then follow the release guide to retain qxctl in a separate new directory.
2. Match the exact operating system and architecture to a ZIP in the [bridge build record](../packaging/beta21/bridge-builds.json). The framework provides macOS 15 ARM64, Ubuntu 24.04 AMD64, Ubuntu 24.04 ARM64 and Ubuntu 26.04 AMD64. Each plugin build has its own recorded platform, build environment and verification coverage.
3. Install the matching ZIP through the host’s supported local plugin installation path. Run the `symphony-setup` skill to select the retained qxctl and create the private read-only connection profile. The plugin starts its own `bin/symphony-mcp` with its own `catalog/tools.json`.
4. Inspect `symphony_connection`, check the bridge version and selected registry, then call an individual read tool such as `symphony_sov_remote_template`. The catalogue includes 303 reads, 220 previews, 220 applies and the connection tool, covering 523 native contracts.

## Published ZIP verification

All four published ZIPs passed clean framework and plugin installation on their native release hosts. The installed bridge answered directly over STDIO. A new Codex conversation resolved the read-only connection, discovered all 744 tools, and completed the SOV target-configuration template call with native exit code 0. [Published release verification](https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills/actions/runs/45471219840).

## Ubuntu 24.04 ARM64 candidate

The Ubuntu ARM64 candidate ran with the signed ARM64 qxctl in an offline emulated Ubuntu 24.04 environment. All three version checks returned `0.2.0-beta.2.1`, all 744 tool names matched the released catalogue, and the native target-configuration template read succeeded. Eight of ten original fixture suites passed. Two encountered test deadlines under emulation. See the [per-profile verification record](../packaging/beta21/bridge-builds.json) for the exact checks and supplemental results.

The same published ZIP subsequently passed a clean installation on a native GitHub-hosted Ubuntu 24.04 ARM64 runner. A fresh Codex conversation discovered all 744 tools, reported bridge version `0.2.0-beta.2.1`, and completed the SOV target-configuration template read. [Native ARM64 installation and tool results](https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills/actions/runs/45461002602/job/138683233815).

## Verify the package inputs

The [signed release index](https://github.com/QuanuX/symphony-distribution/releases/download/v0.2.0-beta.2.1/release-index.json) has SHA-256 `69c89fef8a2ab2eed8e78b56168fcdbbf285989fedf698a43ea499cd2883e9f0`. Use the release verifier and certificate pins in the [installation guide](https://github.com/QuanuX/symphony-distribution/releases/download/v0.2.0-beta.2.1/BETA-INSTALL.md) to verify the index, the selected client carrier and qualification evidence. Extract the original `client.zip` from that carrier. The [release inputs](../packaging/beta21/release-inputs.json) record each platform’s carrier, qxctl, original bridge, catalogue and source lineage. The framework's original bridge reports `0.2.0-alpha.1`.

The [bridge build record](../packaging/beta21/bridge-builds.json) pins the new binary bytes for each available review profile, the runtime version, and the source used to compile them. The `symphony.beta-review-package.v2` receipt in the ZIP contains both sets of identities. Its `files` map covers every other archive member. The existing MCP Registry bundle has its own [published checksum and version](mcp-registry.md).

## Reproduce the review package

Use the committed packaging source and the exact bridge and released client inputs for the same profile. Run the following command from the clean checkout with paths to the new executable, extracted original client and a new output file.

```sh
python3 scripts/package_beta_review.py \
  --profile ubuntu26.04-amd64 \
  --released-client /absolute/verified/original-client \
  --bridge /absolute/verified/beta21-build/symphony-mcp \
  --output /absolute/output/symphony-0.2.0-beta.2.1-ubuntu26.04-amd64.zip
```

The packager compares the original files and new bridge to their independent pins and emits a deterministic ZIP plus SHA-256 sidecar. For OpenAI review, select the single ZIP that matches the intended reviewer host.
