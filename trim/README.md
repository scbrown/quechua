# The trim

Quechua keeps only its differentiated terms. Every term in `ns.ttl` has exactly
one row in `classes.tsv` or `properties.tsv`:

| cell | meaning |
| --- | --- |
| `term` | the local name in `https://scbrown.github.io/quechua/ns#` |
| `decision` | `KEEP`, `DROP` or `INFRA` |
| `relation` | `KEEP`: `subClassOf`, `subPropertyOf`, `closeMatch`, or `none` (properties only). `DROP`: `isReplacedBy`. `INFRA`: empty |
| `target` | a prefixed public term (`schema:Action`), or a kept Quechua term for a local parent |
| `note` | why, in a few words |

- `KEEP`: the term has no public equivalent. Its alignment is published in
  `alignments.ttl`. Every kept class reaches a public parent, directly or
  through kept Quechua parents.
- `DROP`: a public term covers it. The order of preference is a W3C
  Recommendation, then schema.org, then another public vocabulary.
- `INFRA`: homelab- or tool-specific. It is deprecated with no public
  replacement.

Prefixes are the ones pinned in `../vocab/SOURCES.tsv`, plus `rdf` and `rdfs`.
A target the pinned vocabulary does not define is refused.

Property defaults came from shape usage: a property only kept classes use was
kept, and one only homelab classes use was marked homelab. Every other property
was decided by hand, and generic names (`name`, `title`, `url`, `createdAt`,
...) point at their public equivalents wherever they are used.

After editing a table, run `uv run --locked --script scripts/trim.py --write`,
then `--selftest`.
