# Changelog

All notable changes to the Quechua vocabulary. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions are
[semantic](https://semver.org/) as they apply to a vocabulary: a removed or
renamed term is a MAJOR change, an added term is MINOR, and a label or
documentation fix is PATCH.

`ns.ttl` declares its own version (`owl:versionInfo` on
`<https://scbrown.github.io/quechua/ns>`). CI refuses a version with no section
here, and each release publishes that section as its notes.

## [Unreleased]

## [0.5.0] - 2026-10-07

Quechua becomes a thin profile over public vocabularies. It keeps only the
terms that no public vocabulary covers, and every other term points at the one
to use. No term is removed, so every published IRI still resolves.

### Added

- `alignments.ttl`: the nearest public parent or match for each kept term
  (`rdfs:subClassOf`, `rdfs:subPropertyOf`, `skos:closeMatch`). It is a separate
  file because subclass axioms are inferential, so loading them is opt-in. It is
  also published as a release asset.
- `trim/classes.tsv` and `trim/properties.tsv`: one decision per term (KEEP,
  DROP or INFRA), with the target and a reason.
- `vocab/`: pinned term lists for schema.org 30.1, PROV-O, ODRL 2.2, SOSA,
  DCAT 3, SKOS, ORG, OWL-Time, DCMI Terms, Activity Streams, the VC data model
  and RDF Calendar, with each source's URL and sha256. `scripts/pin_vocab.py`
  regenerates and checks them.
- `scripts/trim.py`: applies the tables and validates them, with 14 failure
  controls. CI and the release lane run it.

### Deprecated

- 83 terms that a public term covers (45 classes, 38 properties). Each one is
  marked `owl:deprecated true` and names its replacement with
  `dcterms:isReplacedBy`. Examples: `WorkItem` is replaced by `schema:Action`,
  `Observation` by `sosa:Observation`, `Policy` by `odrl:Policy`, `Person` by
  `schema:Person`, and `name` by `schema:name`.
- 180 homelab- or tool-specific terms (53 classes, 127 properties), such as
  hosts, containers, services, routes, crew traits and file inventories. They
  are deprecated with a comment and have no public replacement.

### Kept

- 183 terms (38 classes, 145 properties): governance and trust, decisions and
  precedents, blockers and their resolution, golden paths and trajectories,
  failure knowledge, workflow runs and transitions, and requirements with
  their tolerances and metrics.

The shapes still target the deprecated classes in this release. They are
retargeted at the replacement classes in the next one.

## [0.4.0] - 2026-10-06

### Added

- `shapes/ontology.shapes.ttl`: 104 shapes and 29 subclass axioms for the
  general knowledge graph (infrastructure, code and repositories, documents
  and media collections, failure knowledge, directives and policies). As with
  the other files, they are the shapes a live store enforces with only the
  namespace renamed; shapes that depend on crew and personal terms not yet in
  the catalog are omitted.
- Twenty catalog terms those shapes use: the classes `CLITool`, `Container`,
  `FileCollection`, `GitRepository`, `IncidentClass`, `Procedure` and `Repo`,
  and the properties `byteCount`, `extensionCounts`, `fileCount`,
  `governedBy`, `hasExtension`, `heldOn`, `inExport`, `newestMtime`,
  `parentCollection`, `relativePath`, `result`, `trackedBy` and `verifiedAt`.
- A conforming ontology example and eleven invalid variants of it.

## [0.3.0] - 2026-10-06

### Added

- `shapes/camayoc.shapes.ttl`: Decision, Verification, ExecutionPath,
  NonFunctionalRequirement, Metric and its derivation, the golden-path records
  (Trajectory, Step, GoldenPath, PathOmission, PathPromotion), Session,
  UsageRecord, review ages and IRI-valued ownership. As with the work-item
  shapes, they are the shapes a live store enforces with only the namespace
  renamed.
- A conforming camayoc example and fifteen invalid variants of it.
- Releases publish every shapes file as `quechua-<name>-shapes-vX.Y.Z.ttl`.

## [0.2.0] - 2026-10-06

### Added

- The first published SHACL shapes, `shapes/work-item.shapes.ttl`: the
  WorkItem, WorkItemScope, Blocker and Observation shapes for projecting an
  issue tracker into RDF. They are the shapes a live store enforces, with only
  the namespace renamed.
- The `inWorkflowRun` property, which the WorkItem shape uses.
- `scripts/check_shapes.py`: every Quechua term a shape uses must be declared
  in `ns.ttl`; a conforming example must validate, and eleven invalid examples
  must each fail on the constraint they break.
- Releases also publish `quechua-work-item-shapes-vX.Y.Z.ttl`.

## [0.1.0] - 2026-10-01

### Added

- The first versioned release of the public declaration catalog: every class
  and property the aegis ontology and its SHACL shapes use, under
  `https://scbrown.github.io/quechua/ns#`, each with its local-name label.
- The reaction and rule-case vocabulary.
- An ontology header in `ns.ttl` carrying `owl:versionInfo`, so a consumer can
  read which release it loaded.
- Tagged releases: `quechua-ns-vX.Y.Z.ttl` and `SHA256SUMS.txt`, so consumers
  pin a digest instead of the moving Pages copy.

[Unreleased]: https://github.com/scbrown/quechua/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/scbrown/quechua/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/scbrown/quechua/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/scbrown/quechua/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/scbrown/quechua/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/scbrown/quechua/releases/tag/v0.1.0
