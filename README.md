# Quechua

A shared vocabulary for knowledge, governance, and code intelligence.

- Namespace: `https://scbrown.github.io/quechua/ns#`
- Prefix: `quechua:`
- [Human-readable catalog](https://scbrown.github.io/quechua/ns)
- [Turtle vocabulary](https://scbrown.github.io/quechua/ns.ttl)

The catalog declares 129 classes and 296 properties extracted from
seven loaded shape sets. It is an initial publication, not a complete validation
schema. Publishing these declarations does not migrate a store, enable
inference, or change instance identifiers.

Instance identifiers remain independent of the vocabulary namespace. Existing
integrations need compatibility checks before changing the terms they use.

## Releases and pinning

The Pages copy of `ns.ttl` follows `main` and changes without notice. To pin,
use a release: each `vX.Y.Z` tag publishes `quechua-ns-vX.Y.Z.ttl` and
`SHA256SUMS.txt`. The file declares its own version as `owl:versionInfo` on
`<https://scbrown.github.io/quechua/ns>`, and the release refuses a tag that
disagrees with it. Changes are listed in [CHANGELOG.md](CHANGELOG.md). Removing
or renaming a term is a major version.

GitHub Pages serves the repository root. The namespace document is `ns.html`;
its extensionless URL must be checked after deployment. It links to `ns.ttl`
as its machine-readable alternative.

## Validation

Run `uv run --locked --script scripts/check_catalog.py --selftest` to parse the
Turtle, check declaration types and labels, and compare its terms with the HTML
anchors. The command also verifies rejection of nine deliberately invalid copies.
CI runs the `Validate vocabulary` check on every pull request, without path
filters, and on pushes to main. Dependencies are pinned in the script lockfile.
This checks the repository artifacts; deployed HTTP responses need a separate
hosting check.
