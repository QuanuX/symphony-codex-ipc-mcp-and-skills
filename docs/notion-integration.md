# Notion agents and local Symphony

Status: optional development adapter. Fixture tests do not establish real Notion
Desktop/Agent qualification or Marketplace acceptance. The gateway is not included
in existing released binaries or the pending OpenAI review archive.

## Connection and authority

Notion Agent → authenticated HTTPS → user-owned proxy/tunnel → loopback C++ MCP
gateway → shared local Bridge core **or** existing same-UID plugin IPC socket →
pinned qxctl → native owners. No GUI or mandatory web API is added to Symphony.

The gateway uses the existing MCP **2025-11-25** baseline. It implements the JSON
response form of Streamable HTTP at `/mcp`; GET returns 405, notifications return
202, DELETE closes the session. It does not implement legacy HTTP+SSE, unsolicited
events, resumable streams or the newer protocol's semantics. Actual Notion
protocol negotiation remains a release check.

The default build stays local-only. Build the optional executable with:

```sh
cmake -S . -B build-gateway -DSYMPHONY_BUILD_GATEWAY=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-gateway -j 2
ctest --test-dir build-gateway --output-on-failure
```

Requirements are the existing C++26 compiler/CMake toolchain. Linux also needs
OpenSSL 3 Crypto. The pinned MIT cpp-httplib source is vendored; builds download
nothing. Python 3.11+ is needed only for configuration/publishing helpers and tests.

## Pair a selected installation

Create the ordinary pinned connection with `scripts/configure_connection.py`.
Then create a new private gateway directory, selecting exact command IDs from that
installation's registry:

```sh
python3 scripts/configure_gateway.py --output /absolute/private/notion-gateway \
  --installation workstation-research \
  --connection /absolute/private/connection.json \
  --host symphony.example.org \
  --command qxcmd:symphony:REPLACE_WITH_DISCOVERED_COMMAND
build-gateway/symphony-mcp-gateway --config /absolute/private/notion-gateway/gateway.json
```

Replace examples with actual discovered values. The helper prints credential
**paths**, never tokens. It does not install services, open a tunnel or select a
different Symphony installation. Read-only tools are enabled; an empty command
list permits connection/discovery but no command execution. An explicit
`--command '*'` permits all eligible commands within the local profile; prefer
task-specific IDs where practical. `--allow-writes` adds prepare/apply, and each
non-read command must independently be enabled in the local connection profile.

For the existing plugin IPC server, replace `--connection` with
`--connect-socket /absolute/private/bridge.sock`. The IPC server must already be
running under the same UID. Its existing serial-session limitation requires
`max_sessions: 1`; close the HTTP session before another client uses that socket.
Direct shared-core mode supports multiple isolated sessions without this socket
limitation. All gateway operations are serialized; it is not a high-throughput
multi-tenant service.

## HTTPS and Notion

The listener binds **127.0.0.1 only**. Use an operator-controlled HTTPS reverse
proxy on the same host, or an outbound authenticated tunnel to a proxy. Templates
are under `adapters/notion/`. Choose the public hostname, infrastructure and TLS
certificate explicitly. Do not expose the raw Unix socket, forward a public
plaintext HTTP port, or use a shared root-owned bridge.

For an outbound tunnel to an existing operator-owned SSH host, forward only its
loopback port and run the HTTPS proxy on that host, for example:

```sh
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -R 127.0.0.1:8765:127.0.0.1:8765 YOUR_EXISTING_HOST_ALIAS
```

The remote server must permit that forwarding, retain `GatewayPorts no`, and
serve the chosen hostname over HTTPS. This command does not provision a host or
enroll credentials. Add a separate 8766 forward only during publisher OAuth if
needed. Stopping the tunnel disconnects the client; it does not roll back work.
The service templates are examples, not installed services. Render exact paths
and validate with the host's service manager before enabling persistence.

The proxy must preserve Authorization, Host, MCP session/version headers and
JSON responses. Put its exact forwarded Host in `allowed_hosts`. Origin, when
present, must exactly match `allowed_origins`; no wildcard/null origins are
accepted. Add a verified client origin if needed, not a guessed broad domain.
The gateway intentionally supplies no browser CORS grant. TLS and external
rate limits belong to the chosen edge. Do not enable proxy request-body or
Authorization logging. Disable proxy retry/failover for POST.

In an eligible Notion workspace, enable custom MCP servers as required by its
admin policy. Add `https://YOUR_HOST/mcp` and header authentication:
`Authorization: Bearer TOKEN_FROM_PRIVATE_FILE`. Treat the connection credential
as a secret. This implementation uses Notion's documented header-auth option;
it does **not** operate an MCP OAuth authorization server or DCR service.

Each configured client has its own `id`, `token_file`, `allowed_tools`, and
`allowed_commands`. To add another agent, create a different random token file
(43–128 URL-safe characters, no newline, mode 0600) and client entry, then restart.
Do not reuse a token between clients. Removing its file revokes future requests;
rotating its contents also invalidates previous sessions. Changes to profile
scope require restart. Revocation does not roll back an operation already admitted.

Notion sharing matters: people interacting with a shared Custom Agent may use
the authenticating connection's authority. A connection ID is not proof of the
individual chat participant's identity. Default write confirmations in Notion
supplement, rather than replace, the local prepare/apply and native authority.

## Recovery and data disclosure

Sessions bind to a connection credential and expire after configurable inactivity
(default ten minutes). A missing/expired/restarted session returns 404; create a
new session but reconcile any uncertain write first. Request IDs are single-use:
an identical retry returns its retained response, changed contents return 409.
The bounded response cache is in memory, not an exactly-once execution guarantee
across restarts. Capacity exhaustion requires a new session, not automatic replay.
An IPC failure invalidates its session and reports an unknown outcome.

The private append-only audit records installation, connection, operation IDs,
method/tool and transport milestones. It omits tokens, arguments and owner
outputs. A dispatch without a response-ready record is unresolved; owner receipts
are authoritative. Connection and command output can still include paths and
sensitive domain data. Notion and any terminating proxy receive tool inputs and
results. Self-hosted computation does not mean these results stay on the machine.

## Actual-host acceptance

Record Notion plan/client version, platform, gateway/source digest and selected
installation. Prove: authenticated initialize; scoped tools; one bounded read;
denied tool/command; isolated connection; one **authorized disposable** mutation;
owner refusal; lost-response reconciliation; token revocation; restart/reconnect.
Check external TLS, proxy retry behavior, Host/Origin and log redaction. Do not
infer these from fixture results or a Connected badge.

Official references checked 2026-11-04:

- [Notion Agent MCP](https://www.notion.com/en-gb/help/connect-mcp-servers-to-your-notion-agent)
- [Custom Agent authentication, sharing and permissions](https://www.notion.com/help/mcp-connections-for-custom-agents)
- [Selected MCP transport specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [Publishing into Notion](notion-publishing.md), [marketplace preparation](notion-marketplace.md)
