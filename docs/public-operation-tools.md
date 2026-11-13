# Individually exposed tools — public review candidate

OpenAI Support case **19173422**, November 5, 2026, identifies operation-level
tool exposure as an additional review requirement. The public package now starts
the local C++ server with `--tool-catalog ${PLUGIN_ROOT}/catalog/tools.json`.
No HTTPS endpoint or Symphony GUI is added. Partner approval and organization
allowlisting remain separate prerequisites.

## Public interface

The versioned catalogue contains **743 operation tools for 523 command contracts**
from the selected review installation, plus the bridge's `symphony_connection`
tool. Read commands have one named tool. Each non-read command has its own
`_preview` and `_apply` tools. Public MCP `tools/list` pages 50 tools at a time.
Clients must follow `nextCursor` to obtain the full inventory.

For example:

- `symphony_sov_remote_template` reads a selected native template using its named
  `operation` parameter. It cannot execute the operation described by that template.
- `symphony_sov_target_inspect` inspects the selected configuration.
- `symphony_sov_target_configure_preview` prepares the exact configure arguments.
- `symphony_sov_target_configure_apply` consumes only a configure preview from the
  same session, once. An evidence or remove preview cannot be substituted.

Each descriptor includes an input schema, output schema, description, native
contract and explicit safety annotations. Values and positional parameters are
named fields, not an arbitrary command ID, route, flags object or argv string.
Native owners still validate required domain inputs and authority.

The public mode refuses calls to the generic discover/describe/read/prepare/apply
tools even if a client guesses those names. Installed commands absent from the
catalogue are not callable. Before dispatch, the exact native command record must
match the packaged binding. An unavailable or changed native contract is an error,
not a reason to select another operation or fall back to a generic executor.

For IPC, start the listener with the catalogue argument. The relay cannot impose
a catalogue on a server started in legacy mode. An explicit standalone launch
without a catalogue retains the historical integration interface for independently
configured clients; that is not the public plugin's configured review surface.
The separately published MCP Registry bundle is not replaced by this candidate.

## Review and regeneration

`scripts/build_tool_catalog.py --qxctl ABSOLUTE_QXCTL --output NEW_CATALOG.json`
binds a trusted local executable, reads its manifest and requests native help.
It never enables a command or invokes an owner operation as a workaround for
missing help. Output creation is exclusive. Review the diff before replacing a
packaged catalogue; generation is a maintainer action, not runtime discovery.

This is a **generated candidate, not a claim of approval or completed metadata
review**. In particular:

- The six prior STAV/Accordare help failures are repaired in the paired W13
  native source. All 523 exposed contracts pass native help; this establishes
  dispatch/help availability, not installed producer or grant authority.
- Generated descriptions and native input-file protocols need owner-by-owner
  review for clear purpose, required arguments, side effects and any nested
  operation selectors. Separate materially different operations if a native
  command still multiplexes them; do not label generation alone as compliance.
- Read/write classification follows the pinned native registry. Apply tools use
  conservative destructive annotations; execution tools use conservative
  open-world annotations. Refine those only from verified behavior before review.
- These are command-level schemas. Native input JSON referenced by a file is
  validated by its owner; this catalogue does not invent a complete domain schema.
- Repeat client selection/evaluation, clean desktop install and demo checks
  against this interface. Historical generic-tool recordings are not evidence
  for the new public tool names.

Existing private profiles retain their selected executable, registry and explicit
non-read enablement. The catalogue does not grant authority, enable operations,
alter Symphony's registry, or constrain independently composed Symphony systems.

Official guidance, checked November 5, 2026:
[tool independence and exposure](https://developers.openai.com/plugins/plugin-guidelines#tool-independence-and-exposure),
[tool design](https://developers.openai.com/plugins/plan/tools),
[desktop-only submission](https://developers.openai.com/plugins/deploy/desktop-only).

`https://localhost` cannot make a user's local server reachable by a hosted MCP
reviewer: loopback names resolve on the caller's machine. For this desktop-only
package, retain stdio and the documented approval path. A remote HTTPS gateway is
a separate deployment choice, not an allowlisting workaround.

W13 reconciles all 525 beta native identities: 523 callable contracts plus the
two documented exclusions. The six former Accordare help gaps are repaired by
core PR #198; the paired qxctl source is recorded in `catalog/beta-source.json`.
See [beta compatibility](beta-compatibility.md) for scope, evidence and release boundaries.
