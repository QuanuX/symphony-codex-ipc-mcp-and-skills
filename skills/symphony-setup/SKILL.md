---
name: symphony-setup
description: Set up or repair this plugin's local Symphony connection, including a matching public-beta profile, by selecting an existing qxctl executable, creating a private pinned connection profile, and verifying the individually exposed read tools through the host.
---

# Set up Symphony

Connect the installed plugin to the Symphony installation the user selected. The bridge is a local executable; setup does not install Symphony or establish a remote service.

For Symphony `0.2.0-beta.2.1`, use the [release-specific setup and provenance](../../docs/openai-beta21-review.md). Preserve the exact released cohort: macOS 15 ARM64, Ubuntu 24.04 AMD64, Ubuntu 24.04 ARM64 or Ubuntu 26.04 AMD64. Use a fresh private installation prefix and a separate new retention directory when installing beta.2.1. Select the retained qxctl and the bridge inside the matching plugin ZIP. An existing user's separate installation remains their selection; do not silently replace it with the beta.

1. Locate this plugin's root and host-provided persistent plugin data directory. Read `package-profile.json` when present and require its `symphony.beta-review-package.v2` schema and exact beta.2.1 cohort. Use its artifact and source identities for the checks below. A source checkout without that receipt is a developer setup, not a verified profile package; resolve its executable and catalogue explicitly. Read [the connection profile contract](../../docs/connection-profile.md). Resolve the selected qxctl executable and working directory from the user's request or existing installation evidence. If several installations are plausible, ask which one to use before pinning one. Do not select a different version to make a failing check pass.
2. Check the package's profile and provenance against the executing operating system, architecture and selected qxctl. Ubuntu 24.04 and 26.04 AMD64 are separate qualified cohorts. Keep the matching binary and `catalog/tools.json` together; never copy a catalogue from another cohort or regenerate one merely to bypass a mismatch. Check that the plugin bridge reports `0.2.0-beta.2.1` and its digest matches `bridge_build.sha256`. The framework’s original retained bridge reports `0.2.0-alpha.1`. Select the binary supplied inside this plugin. Read [host compatibility](../../docs/host-compatibility.md) for standalone or Windows-to-WSL configuration. Historical WSL checks and generic ARM64 builds do not establish beta.2.1 Windows or DGX/Spark qualification.
3. For the packaged OpenAI plugin, its MCP entry reads `${PLUGIN_DATA}/connection.json`. Use the actual host-resolved data directory, not the literal placeholder or a guessed home-directory path. Create its parent privately if needed. If that location is unavailable, generate a standalone Codex configuration fragment targeting an explicit private profile and this package’s `catalog/tools.json` through `--tool-catalog`, explain the selected mode, and preserve existing host settings.
4. Run the packaged `scripts/configure_connection.py` with `--qxctl`, `--working-directory`, and `--output` using those exact absolute paths. The helper requires Python 3.11 or newer and creates the profile exclusively with mode 0600. Start with the default read-only profile. Never overwrite an existing profile blindly: inspect its nonsecret selection and preserve it before a user-requested replacement. Do not print credential-bearing environment values.
5. Reload/reconnect the Symphony MCP connection using the host's supported mechanism. Call `symphony_connection` and select an appropriate individually exposed read tool. Use its exact schema, not generic command IDs. The packaged MCP entry must include `--tool-catalog` with the bundled `catalog/tools.json`. Do not remove that argument to make an unavailable operation execute. Report observed bindings and the bounded read result; tool presence does not establish service health.

The beta.2.1 catalogue describes 523 native command contracts through 303 read,
220 preview and 220 apply tools, plus connection inspection: 744 tools total.
Use that as the package census, not a guarantee that every operation is available
or authorized on the selected installation. The host may paginate the list.

A missing connection profile can make the MCP server fail at first launch; the packaged setup skill remains the route to configuring it. If the host requires a new session or restart, state that remaining step accurately. Do not claim a connection merely because a configuration file was written.

Only enable specific non-read command IDs when the user has requested the corresponding administration and the installation's native authority is available. Setup neither grants native permissions nor authorizes arbitrary later mutations. Use the administration skill for an actual operation and preserve owner refusal/recovery semantics.
