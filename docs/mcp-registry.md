# Symphony MCP Registry distribution

The checksum-pinned root `server.json` describes the published [**0.1.0-alpha.1 MCP Bundle (`.mcpb`)**](https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills/releases/tag/v0.1.0-alpha.1-mcpb). That release contains the C++ bridge, corresponding source and licenses, bundled skills and setup scripts, and four platform executables. Its six-tool interface and original platform evidence apply to that exact artifact.

The current legacy MCPB build template is separately versioned **0.2.0-alpha.1**. It supplies 743 individual operation tools plus connection inspection, 744 total, but has not replaced the published bundle. The [beta.2.1 OpenAI package refresh](openai-beta21-review.md) is a separate profile-specific distribution with its own package version and provenance. Registry publication does not establish OpenAI approval or native Symphony service health.

## Install the published 0.1.0-alpha.1 bundle

These instructions describe the published alpha bundle, not beta.2 qualification. Use its bundled setup script or the corresponding release checkout. The MCPB host asks you to select an existing Symphony connection profile. Before installing, select the intended independently installed `qxctl` and working directory, then create a private profile:

```sh
python3 scripts/configure_connection.py \
  --qxctl /absolute/installation/bin/qxctl \
  --working-directory /absolute/Symphony \
  --output /absolute/private/connection.json
```

This setup requires Python 3.11+. It pins the selected qxctl executable and command registry. The profile must be owned by your user and have mode `0600` or stricter; its containing private directory should be mode `0700`. The default profile enables reads only. Specific non-read commands require explicit profile configuration; native owner authorization and recovery contracts still apply. Do not place your profile in the source repository or inside a release bundle.

Install the published `.mcpb` through your MCPB-compatible client's normal bundle installation flow and select that profile when prompted. The manifest launches `/bin/sh` with a bundled launcher and profile path as separate arguments. The launcher selects an included executable based on the current operating system and architecture, then replaces itself with that executable. It does not download, build, install Symphony, start a background service, or change permissions at launch. This is a C++ server; the shell only chooses its executable.

Clients without MCPB installation can extract the archive and use this explicit stdio command:

```json
{
  "mcpServers": {
    "symphony": {
      "command": "/bin/sh",
      "args": [
        "/absolute/extracted-bundle/launcher.sh",
        "--config",
        "/absolute/private/connection.json"
      ]
    }
  }
}
```

Use normal client configuration for Claude, Codex, VS Code or another MCP host; consult its documented MCP configuration format. The published 0.1.0-alpha.1 bundle includes six Symphony tools (connection, discovery, description, read, prepare and apply), resources, the administration prompt, and its bundled skills. Whether a particular client also imports bundled skills is a separate client capability. The command above intentionally describes that older interface; the current catalogue-based build template additionally requires `--tool-catalog`.

## Published alpha platform scope

The following is the existing alpha distribution and qualification scope. It does not qualify these targets for Symphony beta.2.

| System | Included target | Runtime requirements and limits |
|---|---|---|
| macOS Intel | `darwin-x86_64` | `/bin/sh`, an independently installed compatible qxctl; unsigned Alpha executable |
| macOS Apple Silicon | `darwin-arm64` | macOS 14 deployment target; hosted runtime qualification on macOS 15/26; unsigned Alpha executable |
| Ubuntu LTS x86-64 | `linux-x86_64` | Ubuntu 22.04 or newer; OpenSSL 3 `libcrypto`, compatible `libstdc++`/glibc runtime, `/bin/sh`, compatible qxctl |
| Ubuntu LTS ARM64 | `linux-aarch64` | Same runtime requirements; launcher accepts `uname -m` of `aarch64` or `arm64` |

The package has no native Windows executable. Run the Linux target inside a qualified WSL 2 guest using the separately documented [WSL adapter](windows-wsl2.md); the MCPB manifest intentionally declares only `darwin` and `linux`. The launcher rejects other operating systems or architectures. DGX/Spark hardware qualification remains deferred. A Linux package is not evidence of a DGX deployment.

macOS binaries are unsigned and are not claimed to pass Gatekeeper or notarization checks. Use your normal host and OS policy; this bundle provides no protection bypass. Linux system libraries and `qxctl` are prerequisites, not bundled dependencies. Existing platform reports document the precise fixture/build tests and their limits; registry packaging does not repeat or broaden those claims.

## Build an unpublished 0.2.0-alpha.1 MCPB candidate

The legacy builder reads its version from `packaging/mcpb/manifest.json`, independently of the OpenAI `plugin.json` version and the bridge's runtime version. Its manifest supplies `--tool-catalog` with the bundled `catalog/tools.json`; the candidate interface contains 303 read, 220 preview and 220 apply tools plus connection inspection, covering 523 native command contracts. When configuring this candidate manually, include `--tool-catalog` and the exact extracted catalogue path in addition to the connection profile.

This builder still requires four generic architecture targets, including Intel macOS and one Linux AMD64 slot. Those are not the four beta.2 cohorts: beta.2 has no Intel macOS profile and separately qualifies Ubuntu 24.04 and 26.04 AMD64. Use the [exact beta.2 profile and artifact rules](openai-beta2-refresh.md) for the new OpenAI ZIPs; do not substitute those four cohorts into this legacy target model or infer beta.2 qualification from earlier tests.

Use four previously built and qualified executables whose corresponding source matches the checkout. Stage or commit the packaging files first: the packager includes selected **tracked** repository files only, rejects symlinks and private connection profiles, and does not copy working directories, build caches, authentication tokens or private evidence. Runtime checks and binary-to-source provenance remain the release operator's responsibility.

The following URL is a proposed destination for a new candidate, not a claim that this release exists. Confirm that the selected tag and asset name are unused before publication; do not point new bytes at the already published 0.1.0-alpha.1 artifact.

```sh
python3 scripts/package_mcpb.py --source-root . \
  --binary darwin-x86_64=/absolute/qualified/darwin-x86_64 \
  --binary darwin-arm64=/absolute/qualified/darwin-arm64 \
  --binary linux-x86_64=/absolute/qualified/linux-x86_64 \
  --binary linux-aarch64=/absolute/qualified/linux-aarch64 \
  --output /absolute/output/symphony-0.2.0-alpha.1.mcpb \
  --release-url https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills/releases/download/v0.2.0-alpha.1-mcpb/symphony-0.2.0-alpha.1.mcpb
```

The command checks executable format/architecture headers and emits the deterministic MCPB, SHA-256, a `.server.json` registry manifest, and a `.package.json` provenance receipt. Existing output files are never replaced. A supplied release URL is a destination description; creating metadata does not create a release or prove the asset is accessible.

Retain the original runtime qualification and binary digests, verify the final extracted bundle with focused read-only fixture tests, and upload the exact `.mcpb` and corresponding source to the specified public GitHub Release. The registry manifest's `fileSha256` binds the uploaded file bytes.

Keep root `server.json` and the registry workflow pinned to the published 0.1.0-alpha.1 bundle until a real replacement is independently qualified and published. The existing workflow downloads and exercises that exact alpha artifact; its successful checks do not validate a new candidate or a beta.2 profile.

## Publish and verify

The official Model Context Protocol Registry is a metadata catalogue. It accepts publication through `mcp-publisher` from this repository; PRs adding listings to `modelcontextprotocol/registry` do not publish servers. The registry identity is `io.github.QuanuX/symphony`, with a pinned MCPB release URL and `stdio` transport. No hosted remote endpoint is declared.

Use the current official publisher with namespace-authorized GitHub OAuth or GitHub Actions OIDC. In an authorized workflow, `mcp-publisher login github-oidc` uses a job-scoped OIDC token with `id-token: write`; no long-lived personal token is necessary. Publish only after the referenced release asset is publicly readable and the metadata passes the official validation available in that publisher version. Confirm publication by reading the resulting record from the production registry, including version and package hash. Do not equate a local validation or workflow start with successful publication.

GitHub's MCP catalogue is a downstream, curated surface. Its published guidance requests contacting `partnerships@github.com` for initial inclusion after official registry publication. A successful official-registry record does not itself prove that the server is visible at `github.com/mcp`; verify each outcome separately.

References checked for this packaging increment:

- [Official publishing quickstart](https://modelcontextprotocol.io/registry/quickstart)
- [Supported packages and MCPB requirements](https://modelcontextprotocol.io/registry/package-types)
- [MCPB manifest format](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md)
- [GitHub Actions publishing](https://modelcontextprotocol.io/registry/github-actions)
- [GitHub catalogue publishing guidance](https://github.blog/ai-and-ml/generative-ai/how-to-find-install-and-manage-mcp-servers-with-the-github-mcp-registry/)
