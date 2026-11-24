# Beta.2 plugin package refresh

This refresh aligns the local MCP plugin and its `symphony-setup` and
`symphony-admin` skills with the published Symphony `0.2.0-beta.2` release.
Package construction and compatibility checks do not establish OpenAI review
eligibility, acceptance or publication.

## Released baseline

Use the [published beta.2 release](https://github.com/QuanuX/symphony-distribution/releases/tag/v0.2.0-beta.2)
and its [installation guide](https://downloads.quanux.org/symphony/0.2.0-beta.2/docs/BETA-INSTALL.md).
The release index, detached signature and publisher verification instructions
identify the exact downloadable artifacts. Preserve their relative paths and
verify the selected downloads before using them.

| Identity | Value |
| --- | --- |
| Symphony framework release | `0.2.0-beta.2` |
| Refreshed package version | `0.2.0-beta.2` |
| Bridge runtime reported by the released client | `0.2.0-alpha.1` |
| Actual native build source | [`QuanuX/Symphony@bae2e817120467561ae051c1b08cf61be3436bac`](https://github.com/QuanuX/Symphony/tree/bae2e817120467561ae051c1b08cf61be3436bac) |
| Published beta's original client source | [`572627e939250763756167a9dc05d8cb37ab4e30`](https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills/tree/572627e939250763756167a9dc05d8cb37ab4e30) |

The bridge runtime and framework release have separate version identities.
Updating package metadata or skills does not change a compiled executable's
version or source. Retain the original build provenance and bind the selected
binary and catalogue hashes in each new package receipt.

## Exact supported profiles

| Operating system | Architecture | Selection boundary |
| --- | --- | --- |
| macOS 15 | ARM64 / Apple Silicon | Use the Mac ARM64 client and catalogue. |
| Ubuntu 24.04 | AMD64 | Use the 24.04 cohort, including its qxctl and catalogue. |
| Ubuntu 24.04 | ARM64 | Use the Linux ARM64 client and catalogue. |
| Ubuntu 26.04 | AMD64 | Use the separately qualified 26.04 cohort. |

The two AMD64 Linux cohorts share a Conda subdirectory but are separate
qualified builds. A beta.2 macOS Intel profile is not supplied. Historical WSL
adapter checks and generic ARM64 binaries do not establish beta.2 Windows or
NVIDIA DGX/Spark qualification.

The Mac distribution uses a detached publisher signature; that does not supply
Apple Developer ID signing or notarization. Preserve the release guide's host
approval and trust boundaries.

## Installation and connection

1. Follow the release guide to verify and install one exact profile into a new
   private prefix.
2. Retain its qxctl and client in a separate new private custody directory using
   the guide's verified retention index. Use the retained pair for client setup.
3. Select the corresponding profile-specific plugin package. Keep its bridge,
   catalogue and provenance together; do not mix artifacts across cohorts.
4. Use the packaged setup skill to select the user's workspace and create a new
   private read-only connection profile. Preserve any existing host selection.
5. Reconnect through the host's supported mechanism, inspect
   `symphony_connection`, and execute an appropriate individual read tool.
   Record the observed selection and result within its actual scope.

Beta.1-to-beta.2 in-place native upgrade and rollback are not qualified. Use a
fresh prefix and separate retention directory. Installing or removing a carrier
package does not itself change retained binaries, active profiles or native
service state.

## Interface and verification boundary

The beta.2 client catalogue covers **523 native command contracts** with
**303 read tools, 220 preview tools and 220 apply tools**, plus
`symphony_connection`: **744 tools total**. The two intentionally excluded
native records remain `sov.target.invoke` and `stav.append`.

Use each tool's exposed schema. The count is a package census, not a promise
that every native owner is present, authorized or healthy. The bridge checks
the selected registry; native owners retain authority, state preconditions and
recovery semantics. New user-authored commands require an explicit catalogue
update before this public plugin can expose them.

The source reconciliation retains the W13/D07/D08 compatibility verifiers and
catalogue tests. Historical [W13](w13-engineering-handoff.md),
[D07](d07-distribution-handoff.md) and [D08](d08-stamped-owner-handoff.md)
evidence applies to its own source, artifacts and observed hosts. In particular,
do not reuse a historical observed-registry digest for a different beta.2
executable. Each profile requires its actual binding.

## Package and channel boundaries

An OpenAI review ZIP contains one selected platform executable, the matching
catalogue, plugin metadata, both skills, corresponding source and licenses.
Its root `package-profile.json` uses schema
`symphony.beta-review-package.v1` and records the selected profile and artifact
provenance. Read that receipt before configuring the host. A source checkout
without this receipt remains a developer setup with an explicitly selected
executable and catalogue; it is not a verified released-profile package.
Exclude connection profiles, credentials, private transcripts and developer
state. Record archive hashes and the exact scope of validation; do not replace
an already reviewed archive silently.

The previously uploaded alpha draft is a separate immutable review artifact.
Report any new upload or portal validation only after it actually occurs. A
beta package refresh does not resolve representative assignment or local-MCP
eligibility by itself.

The published MCPB and root `server.json` remain at their existing checksum-pinned
release until a real replacement is built and qualified. The legacy MCPB target
model includes Intel macOS and one Linux AMD64 slot, so it cannot be treated as
the four beta.2 cohorts without explicitly resolving that mismatch. A new
profile-specific MCPB must retain its exact cohort and artifact identities;
building it does not establish publication in either registry.

## Reproduce the review package

Use the [historical beta.2 checkout](https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills/tree/28ef2f2) for the following commands.

First verify and extract the exact released client for the selected profile
using the release guide. The checked-in
[input pins](../packaging/beta2/release-inputs.json) bind its carrier URL, binary,
catalogue and qualification evidence to the published beta. The source tree's
catalogue retains the historical D08 reference binding; the review packager
replaces all three generated catalogue files with the selected released
profile's exact files.

Before committing, check the selected inputs without creating an archive:

```sh
python3 scripts/package_beta_review.py \
  --profile ubuntu24.04-amd64 \
  --released-client /absolute/verified/ubuntu24.04-amd64/client \
  --validate-only
```

After committing the complete review source, build outside the checkout:

```sh
python3 scripts/package_beta_review.py \
  --profile ubuntu24.04-amd64 \
  --released-client /absolute/verified/ubuntu24.04-amd64/client \
  --output /absolute/output/symphony-0.2.0-beta.2-ubuntu24.04-amd64.zip
```

Repeat with the exact matching client directory for `macos15-arm64`,
`ubuntu24.04-arm64` or `ubuntu26.04-amd64`. The command requires a clean committed
tree, verifies the released input hashes and unchanged bridge source, and
writes an exclusive archive plus SHA-256 sidecar. It does not upload or submit
the package. Each ZIP has one plugin root; an outer delivery archive containing
multiple profile ZIPs is not itself a plugin submission.

The generic `scripts/package_release.py` remains available for explicitly
selected developer builds and source archives. Its output is not a verified
beta.2 profile package. See [verification scope](beta2-validation.md) for the
checks actually performed and their limits.
