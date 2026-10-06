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

## [0.4.0] - 2026-10-07

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

## [0.3.0] - 2026-10-07

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

[Unreleased]: https://github.com/scbrown/quechua/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/scbrown/quechua/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/scbrown/quechua/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/scbrown/quechua/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/scbrown/quechua/releases/tag/v0.1.0
