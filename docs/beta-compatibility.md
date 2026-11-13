# Public Beta compatibility (W13)

This work qualifies the existing bridge against a specific Symphony source pair.
The feature freeze remains in force. Codex is the primary real client; Claude
Code, Antigravity, generic stdio and explicit Windows-to-WSL adapters remain
maintained. Adapter fixtures do not qualify an actual client or a physical host.
The MCP contract remains 2025-11-25. The candidate remains 0.2.0-alpha.1.

The baseline is Symphony PR #197, merged at
`8e56b1502719c9efc5a3f1179b43234498722370`, and client PR #5 at
`ee086a22d5a5f04ffdebaf06a06008cc70e75fac`. W13 is stacked on client #5;
it does not merge that dependency. See `catalog/beta-source.json` for the exact
qualified native source and `catalog/beta-delta.json` for the reviewed delta.

Default profiles are read-only. Native authority remains mandatory even for
read-classified commands where the owner requires host permission. Non-read
commands require explicit per-command enablement and one-use, operation/session
bound previews. The serial same-user IPC listener supports reconnect, not
concurrent cancellation or streaming. Reconcile uncertain effects with the owner;
do not replay them automatically. Connection metadata is not engine health.

The compatibility companion maps to paper C02.4 and supplemental MCP-CHANNELS.
It keeps core and client repository identities separate. Core's delivery index
continues to permit only its own source for non-vendor native components; a client
package is neither a qxctl artifact nor a vendor payload.

## Review and qualification

Run the focused CTest groups for each affected boundary. At the W13 milestone,
run all CTest groups, packaging tests, the exact staged native-owner lifecycle,
and Codex app-server sessions in an isolated profile. Deterministic app-server
calls establish client transport behavior, not model tool selection, desktop GUI
onboarding, directory approval or live-provider qualification.

The affected-path PR workflow runs bridge, catalog, adapter and evidence fixtures.
The existing manual smoke campaign retains Ubuntu 24.04 x86-64, macOS 15 ARM,
and Windows/Ubuntu 24.04 WSL2. Push increments without waiting for CI; inspect
hosted results before accepting or merging the milestone.

Distribution follows W13: select Anaconda channel/package form, publisher identity,
signatures and independent trust delivery, final URLs/digests, fresh hosts,
rollback policy and independent reviewers. Keep published `server.json` unchanged
until real replacement artifacts exist. No compatibility result grants publication
or closes W12's final artifact/provider/host/review gaps.

## Compatibility packet

Supply independently reviewed `requirements.json`, retained `observations.json`,
and an evidence directory to:

```sh
python3 scripts/verify_beta_compatibility.py \
  --requirements REQUIREMENTS.json --observations OBSERVATIONS.json \
  --evidence-root PRIVATE_EVIDENCE --output NEW_REPORT.json
```

The schema in `schemas/` defines the two input shapes. Requirements fix the two
repository/commit/tree identities, six bindings, artifact paths and digests, and
exact Codex version/OS/architecture/configuration for stdio and same-user IPC.
Each client observation references a separately hashed report with every required
case and hashed transcript attachments. The verifier checks native build identity,
expected/observed record parity, complete catalog census, package inventory and
source inventory. Every package file belongs to the selected plugin source,
except the separately bound compiled bridge. Final-channel fields remain pending.

Exit 1 rejects malformed, contradictory or tampered evidence; exit 2 retains a
valid incomplete packet; exit 0 permits engineering review only. Output creation
is exclusive and private. Paths must stay within the evidence directory, with no
symlinks. JSON, archives and files have explicit bounds. The verifier never runs
attachments and cannot authenticate an operator, compiler or signer: independent
requirements review and retained build/client logs remain essential. Do not turn
a fabricated fixture packet into a real-client claim merely by changing labels.
