# Quechua

A shared vocabulary for knowledge, governance, and code intelligence.

- Namespace: `https://scbrown.github.io/quechua/ns#`
- Prefix: `quechua:`
- [Human-readable catalog](https://scbrown.github.io/quechua/ns)
- [Turtle vocabulary](https://scbrown.github.io/quechua/ns.ttl)
- [Work-item SHACL shapes](https://scbrown.github.io/quechua/shapes/work-item.shapes.ttl)
- [Camayoc SHACL shapes](https://scbrown.github.io/quechua/shapes/camayoc.shapes.ttl)
- [Ontology SHACL shapes](https://scbrown.github.io/quechua/shapes/ontology.shapes.ttl)

The catalog declares 136 classes and 310 properties extracted from
the loaded shape sets. It is an initial publication, not a complete validation
schema. Publishing these declarations does not migrate a store, enable
inference, or change instance identifiers.

Instance identifiers remain independent of the vocabulary namespace. Existing
integrations need compatibility checks before changing the terms they use.

## Shapes

`shapes/` holds SHACL shapes over the catalog's terms. The first set,
`work-item.shapes.ttl`, covers tracker-agnostic work: a `WorkItem`, the scope
it grants, the `Blocker`s it waits on, and the `Observation`s a tracker
projection records. `camayoc.shapes.ttl` covers the records a reader trusts:
decisions, verifications, execution paths, requirements and metrics, golden
paths and cost accounting. `ontology.shapes.ttl` covers the general graph:
infrastructure, code and repositories, documents and media collections,
failure knowledge, and directives with the policies that govern them. Shapes
that depend on crew and personal terms not yet in the catalog are omitted.
`shapes/examples/` has a conforming example for each file.

The shapes keep their deliberate posture: strict on the `sourceKind`
provenance tag, permissive elsewhere. Scope is optional, because unknown scope
advises and never blocks. Shape IRIs share the namespace but are not
vocabulary terms.

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

Run `uv run --locked --script scripts/check_shapes.py --selftest` to check that
every term a shape uses is declared in `ns.ttl`, and that the conforming examples
validate while each invalid variant fails on the constraint it breaks.

Run `uv run --locked --script scripts/check_catalog.py --selftest` to parse the
Turtle, check declaration types and labels, and compare its terms with the HTML
anchors. The command also verifies rejection of nine deliberately invalid copies.
CI runs the `Validate vocabulary` check on every pull request, without path
filters, and on pushes to main. Dependencies are pinned in the script lockfile.
This checks the repository artifacts; deployed HTTP responses need a separate
hosting check.
