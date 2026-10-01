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

[Unreleased]: https://github.com/scbrown/quechua/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/scbrown/quechua/releases/tag/v0.1.0
