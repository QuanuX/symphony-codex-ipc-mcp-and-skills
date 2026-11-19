# Beta.2 review refresh: verification scope

This record describes checks performed on 19 November 2026 for the refreshed
OpenAI review packages. It distinguishes the published beta's evidence from
checks of the refreshed source. It does not establish OpenAI eligibility,
desktop GUI acceptance or live trading behavior.

## Released input integrity

The four client carriers were obtained through the published
[beta.2 release](https://github.com/QuanuX/symphony-distribution/releases/tag/v0.2.0-beta.2)
and [installation guide](https://downloads.quanux.org/symphony/0.2.0-beta.2/docs/BETA-INSTALL.md).
The publisher signature was verified before using the exact released inputs.
Verification followed the release index, signed bootstrap and unit metadata,
Conda carrier, payload manifest, original client ZIP and every client inventory
member. The checked-in [input pins](../packaging/beta2/release-inputs.json) retain
the public URLs and hashes used by the review packager.

The independently published release-index SHA-256 is
`978551b467483a9fc0e583724aefadc962a6fde15617a885272c084bc2f42c0e`.
The verifier linked at distribution revisions `205fd69e0973c8aaa2fbe1a5d4d95082cf1241f4`
and `bd70dc3c3e6204a85a65f2a4de21b29a9dad9cf1` was compared and found byte-identical:
SHA-256 `ad60efa14b3ba901c568d85d9074be6e41be299f939d47e46dc0d64809b06523`.

Each refreshed package retains its selected released bridge and all three
generated catalog files: `tools.json`, `beta-source.json` and
`stamped-owner-delta.json`. Their hashes, the original build sources and the
refreshed review-source commit are recorded in `package-profile.json`.

## Read-only native checks

The exact released Ubuntu 24.04 AMD64 qxctl was verified and inspected with
`--help`, `version --json` and `commands manifest --json` in an isolated working
directory. Its SHA-256 is
`f2539c9222c2cf9ff956692c95002b13121a6f5b851c5fb702b27a1b50ad3fd6`.

- Actual build metadata matched the released `beta-source.json` exactly.
- The actual 525-command registry matched the released observed digest.
- All 523 callable command records matched their catalog bindings exactly.
- The catalog contains 303 read, 220 preview and 220 apply tools. Including
  connection inspection, the public interface has 744 tools.
- The two intentional native exclusions remain `sov.target.invoke` and
  `stav.append`.

Both released AMD64 bridge binaries returned `0.2.0-alpha.1` from `--version`.
The Mac and ARM binaries were inspected statically and retain their signed
release provenance; they were not executed in this workspace. The two AMD64
catalog files are identical, but their bridge binaries differ. The packager
therefore retains separate Ubuntu 24.04 and 26.04 profiles.

These checks did not install a native owner, activate a service, change a
connection profile or exercise live broker operations.

## Refreshed-source checks

The bridge built successfully on Debian 13 with GCC 14.2, CMake 3.31.6 and
OpenSSL 3.5.7. This local build is a source check; the review ZIPs use the exact
released cohort binaries rather than this workspace's build.

The existing catalog, public-operation, client-adapter, qualification-report,
beta-compatibility, distribution-compatibility and bounded-hashing test groups
passed. The MCP integration group passed 19 of 20 cases; its optional Unix
socket case and the transport test group could not complete because this
workspace denies local socket creation (`errno 1`). Those failures remain
reported, with no test removal, weakened assertion or native implementation
change. The repository's Beta compatibility workflow exercises these paths on
its macOS runner; consult the workflow result for the exact review commit.

All eleven legacy MCPB packager tests passed after separating that channel's
manifest version from the beta.2 OpenAI package version. The published MCPB
asset and `server.json` checksum remain unchanged.

Both bundled skills passed frontmatter, relative-link and metadata checks.
A separate read-only setup scenario correctly selected the Ubuntu 26.04
profile, preserved an existing beta.1 installation and distinguished package
version from runtime version. It did not perform a desktop installation.

The new package tests cover deterministic output, clean-source provenance and
rejection of a mismatched cohort, altered released inputs, altered native
sources and unsafe package members. Final archives are built from a clean
committed source tree and receive SHA-256 sidecars.

## Remaining boundaries

The refresh is compatible with the published beta's command contracts. It does
not prove every native owner is installed or authorized, every host imports
the skills, desktop GUI lifecycle acceptance, beta.1 in-place upgrade/rollback,
or live engine execution. OpenAI representative assignment, organization
allowlisting and publication approval remain separate review decisions.
