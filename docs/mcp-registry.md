# Symphony MCP Registry distribution

This repository supplies a native **MCP Bundle (`.mcpb`)** for MCPB-compatible clients. The bundle contains the existing C++ bridge, its corresponding source and licenses, the unchanged skills and setup scripts, and four platform executables. It is separate from the OpenAI plugin ZIP and from OpenAI's public-plugin eligibility process. Registry publication does not establish OpenAI approval or native Symphony service health.

## Install and configure

The MCPB host asks you to select an existing Symphony connection profile. Before installing, select the intended independently installed `qxctl` and working directory, then create a private profile using the bundled or repository setup script:

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

Use normal client configuration for Claude, Codex, VS Code or another MCP host; consult its documented MCP configuration format. The bundle includes six Symphony tools (connection, discovery, description, read, prepare and apply), resources, the administration prompt, and the existing skills. Whether a particular client also imports bundled skills is a separate client capability.

## Platform scope

| System | Included target | Runtime requirements and limits |
|---|---|---|
| macOS Intel | `darwin-x86_64` | `/bin/sh`, an independently installed compatible qxctl; unsigned Alpha executable |
| macOS Apple Silicon | `darwin-arm64` | macOS 14 deployment target; hosted runtime qualification on macOS 15/26; unsigned Alpha executable |
| Ubuntu LTS x86-64 | `linux-x86_64` | Ubuntu 22.04 or newer; OpenSSL 3 `libcrypto`, compatible `libstdc++`/glibc runtime, `/bin/sh`, compatible qxctl |
| Ubuntu LTS ARM64 | `linux-aarch64` | Same runtime requirements; launcher accepts `uname -m` of `aarch64` or `arm64` |

The package has no native Windows executable. Run the Linux target inside a qualified WSL 2 guest using the separately documented [WSL adapter](windows-wsl2.md); the MCPB manifest intentionally declares only `darwin` and `linux`. The launcher rejects other operating systems or architectures. DGX/Spark hardware qualification remains deferred. A Linux package is not evidence of a DGX deployment.

macOS binaries are unsigned and are not claimed to pass Gatekeeper or notarization checks. Use your normal host and OS policy; this bundle provides no protection bypass. Linux system libraries and `qxctl` are prerequisites, not bundled dependencies. Existing platform reports document the precise fixture/build tests and their limits; registry packaging does not repeat or broaden those claims.

## Build the distribution

Use four previously built and qualified executables whose corresponding source matches the checkout. Stage or commit the packaging files first: the packager includes selected **tracked** repository files only, rejects symlinks and private connection profiles, and does not copy working directories, build caches, authentication tokens or private evidence. Runtime checks and binary-to-source provenance remain the release operator's responsibility.

```sh
python3 scripts/package_mcpb.py --source-root . \
  --binary darwin-x86_64=/absolute/qualified/darwin-x86_64 \
  --binary darwin-arm64=/absolute/qualified/darwin-arm64 \
  --binary linux-x86_64=/absolute/qualified/linux-x86_64 \
  --binary linux-aarch64=/absolute/qualified/linux-aarch64 \
  --output /absolute/output/symphony-0.1.0-alpha.1.mcpb \
  --release-url https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills/releases/download/v0.1.0-alpha.1-mcpb/symphony-0.1.0-alpha.1.mcpb
```

The command checks executable format/architecture headers and emits the deterministic MCPB, SHA-256, a `.server.json` registry manifest, and a `.package.json` provenance receipt. Existing output files are never replaced. A supplied release URL is a destination description; creating metadata does not create a release or prove the asset is accessible.

Retain the original runtime qualification and binary digests, verify the final extracted bundle with focused read-only fixture tests, and upload the exact `.mcpb` and corresponding source to the specified public GitHub Release. The registry manifest's `fileSha256` binds the uploaded file bytes.

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
