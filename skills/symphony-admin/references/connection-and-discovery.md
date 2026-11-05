# Connection and discovery

## Connection choices

The host starts `symphony-mcp` as an MCP stdio process. A connection uses either an operator-selected configuration file (`--config` or the runtime's `SYMPHONY_MCP_CONFIG` fallback) or `--connect-socket` to an already running local bridge. The optional daemon is started explicitly with `--config FILE --listen SOCKET`.

The socket belongs to this bridge. It is not a generic pre-existing Symphony administration endpoint, a replacement for native SSIAG/STAV IPC, or a new authority service. Its intended boundary is local, same-user IPC on supported POSIX hosts. Do not expose the socket over a network or substitute a remote endpoint without a separately supported transport and authorization design.

Client registration examples are provided by the package's adapter generator. A missing binary, configuration, socket, or qxctl installation is setup work. Preserve an existing configuration and report the exact missing input; do not invent an installation from repository contents. Never collect credentials in chat.

For a Windows-host client, use the package's `adapters/codex/windows-wsl2.toml.example` or `adapters/generic/windows-wsl2.json.example` and `docs/windows-wsl2.md`. Select the distribution, Linux user and Linux paths explicitly. A Windows client launches the Linux binary through `wsl.exe`; a POSIX executable path alone is insufficient.

## Select an exposed operation

1. Inspect `symphony_connection` when installation identity matters.
2. Use the host's available operation-specific tool definitions. Each includes its own schema, native contract and safety annotations. MCP clients page `tools/list` using its opaque `nextCursor`.
3. Supply the exact named arguments; resolve native requiredness, targets and owner input protocols from the task and owner evidence. A command being listed does not prove that its native contract matches this installation or that the owner can run.
4. Use the operation's read tool, or its matching `_preview`/`_apply` pair. Never substitute a generic executor, shell call or another plugin for an unavailable public operation.

Start the public stdio server with `--tool-catalog ABSOLUTE/catalog/tools.json`. For IPC, the listening server must have that argument; the relay cannot impose a catalogue on a legacy server. The public plugin package supplies the catalogue argument automatically. The separate standalone legacy adapter remains outside this public review interface.

## Arguments and result interpretation

Supply the named top-level parameters in each tool's schema. Value flags are strings to preserve numerical precision, repeated flags are bounded string arrays, booleans are booleans, and positional parameters use `arg_` names. Omit `json`, which the bridge owns. No `command_id`, arbitrary `flags` map, route selector, or command string is accepted by these tools. Native owners still validate domain payloads and requiredness.

The connection pins the qxctl executable and working directory. It does not implicitly bind every command's TOPS identity, scope, installation prefix, or version. Resolve those exact targets through the user's request and the owner's schemas and evidence, then pass the command's supported arguments. A different command-selected target does not by itself require a new profile. Selecting a different executable or working directory uses the documented connection setup workflow. Do not invent missing target choices or native defaults.

The bridge supplies no subprocess stdin payload; qxctl receives an empty stdin stream. An owner protocol requiring a stdin document needs a supported input-file route or an explicit bridge extension. Do not claim that a registry entry or accepted argument grammar guarantees every invocation form is available.

Distinguish these observations:

| Observation | What it establishes |
| --- | --- |
| MCP connection succeeds | The client can exchange protocol messages with this bridge. |
| Command is discovered | The selected qxctl registry advertises that command. |
| Repository status/inventory/doctor succeeds | The reported repository or structural checks succeeded within their documented scope. |
| Exact installation/binding verifies | The reported files, version, receipt, or binding passed the owner's checks. |
| Native service status succeeds | That particular service returned the reported observation at that time. |
| Operation receipt/status confirms completion | The exact recorded attempt reached the owner's reported state. |

## When no operation matches

Try the owner's actual terminology and inspect its registered capabilities. Do not claim an absent operation is available because a white paper names it. If the current bridge cannot expose a needed command, report the concrete gap. User-authored modules and alternative adapters are valid extensions; this Alpha's current registry support is not a universal limit on Symphony.
