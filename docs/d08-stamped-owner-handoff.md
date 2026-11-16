# D08 original-source owner identity

The D08 client uses a new qxctl built twice by the unchanged committed
`symphony.qxctl.reproducible-build.v1` recipe from clean original core Git source
`5fd6cee1bae477048bf0045b691ee8bdf334e216`, tree
`327edd0f22860e84d30fe745f5a2b0e602f4af88`. Both outputs have SHA-256
`abbcdd7e4c66ae74cf5faefe28e30600446d2a1859bb24e4bf04fdd84e40d6b4`.
Its existing embedded build-info contract now truthfully reports `stamped` with
the original source epoch, dependency-map digest and recipe identity. Core code
and both main branches are unchanged.

All 291 Go-selected compiled/embedded module inputs match the reviewed public
derived export. The sole transformed qxctl test fixture is not part of that
compiled closure. The original-Git rebuild is a component-specific source choice;
it does not relabel the other D06 modules or the derived export as an unmodified
Git tree. Private original module archives remain outside distribution packages.
The public compiled-source closure, original recipe and exact build proof are
bound in the separate distribution record.

`catalog/beta-source.json` now records the actual stamp and its original-source
proof. `catalog/stamped-owner-delta.json` records the binary binding change; no
command records or tool descriptors changed. The existing expected registry is
unchanged. The observed registry and catalog hashes are regenerated against the
new executable, and the new packet must run the original W13 compatibility
verifier and actual Codex against its exact packaged bytes. Neither verifier is
relaxed. Historical D07 evidence and its unstamped-owner refusal remain valid
records for the old bytes.

Native bridge/adapter sources and published `server.json` are unchanged. Reusing
the exact independently reproduced bridge requires matching its compiled source
and build rules; it does not reuse the old catalog or actual-client acceptance.
The current client/source/package identities and later actual-client results are
recorded in the [D08 distribution handoff](https://github.com/QuanuX/symphony-distribution/blob/codex/d08-installer-assembly/docs/D08-INSTALLERS.md).

An embedded source identity is not publisher trust. Review self-signing, final
Apple trust/notarization, Anaconda/Cloudflare publication and retrieval, primary
platforms, fresh hosts, remaining lifecycle safety gates and independent release
approval retain their own boundaries. No package extraction grants permission,
starts services or changes a user's application selection.
