# Quechua

A shared vocabulary for knowledge, governance, and code intelligence.

- Namespace: `https://scbrown.github.io/quechua/ns#`
- Prefix: `quechua:`
- [Human-readable catalog](https://scbrown.github.io/quechua/ns)
- [Turtle vocabulary](https://scbrown.github.io/quechua/ns.ttl)
- [Work-item SHACL shapes](https://scbrown.github.io/quechua/shapes/work-item.shapes.ttl)
- [Action governance SHACL shapes](https://scbrown.github.io/quechua/shapes/action-governance.shapes.ttl)
- [Camayoc SHACL shapes](https://scbrown.github.io/quechua/shapes/camayoc.shapes.ttl)
- [Ontology SHACL shapes](https://scbrown.github.io/quechua/shapes/ontology.shapes.ttl)
- [Alignments to public vocabularies](https://scbrown.github.io/quechua/alignments.ttl)

The catalog declares 136 classes and 310 properties extracted from
the loaded shape sets. It is an initial publication, not a complete validation
schema. Publishing these declarations does not migrate a store, enable
inference, or change instance identifiers.

Instance identifiers remain independent of the vocabulary namespace. Existing
integrations need compatibility checks before changing the terms they use.

## A thin profile over public vocabularies

Quechua keeps only the terms no public vocabulary covers: governance and trust
(verdicts, verification, attestations, certification), decisions and their
precedents, blockers and how they resolve, golden paths and trajectories,
failure knowledge, and workflow runs checked against their definitions.
Everything else is a public term with a pointer to it. The preference order is
a W3C Recommendation, then schema.org, then another public vocabulary.

Each term's decision is a row in `trim/classes.tsv` or `trim/properties.tsv`
(see [trim/README.md](trim/README.md)):

- **Kept** terms are aligned to their nearest public parent or match in
  `alignments.ttl` (`rdfs:subClassOf`, `rdfs:subPropertyOf`, `skos:closeMatch`).
  The alignments are a separate file because subclass axioms are inferential:
  loading them changes what a store's type queries return, so a consumer opts in.
- **Replaced** terms stay declared in `ns.ttl`, marked `owl:deprecated true`
  with `dcterms:isReplacedBy` naming the public term to use instead.
- **Homelab-specific** terms stay declared and deprecated, with a comment and
  no public replacement.

No term is removed, so every published IRI still resolves. The replacement
targets are checked offline against pinned term lists in `vocab/`, derived from
the sources and sha256 digests in `vocab/SOURCES.tsv`.

## Shapes

`action-governance.shapes.ttl` applies Quechua's provenance, terminal outcome,
and blocker constraints to public `schema:Action` records. Its blocker targets
must also be Actions. Tracker status, priority, revisions, comments, and calendar
mechanics belong in a separate tracker profile. Loading this governance profile
requires every Action in the validation scope to carry `sourceKind`; publication
alone does not enable it in a store.

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
anchors. The command also verifies rejection of eleven deliberately invalid copies.

Run `uv run --locked --script scripts/trim.py --selftest` to check that every
term has exactly one decision, every replacement and alignment target is defined
by a pinned vocabulary, and `ns.ttl`, `ns.html` and `alignments.ttl` agree with
the tables. After editing a table, `--write` regenerates those three files.
`scripts/pin_vocab.py --check` confirms the pinned sources are still what their
publishers serve; `--update` re-pins them after a deliberate upgrade.
CI runs the `Validate vocabulary` check on every pull request, without path
filters, and on pushes to main. Dependencies are pinned in the script lockfile.
This checks the repository artifacts; deployed HTTP responses need a separate
hosting check.
