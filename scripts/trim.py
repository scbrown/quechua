# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rdflib==7.1.4",
# ]
# ///
"""Apply and validate the trim: Quechua keeps only its differentiated terms.

Every catalog term has exactly one decision in `trim/classes.tsv` or
`trim/properties.tsv`:

  KEEP   the term stays. Its nearest public parent or match is published in
         alignments.ttl (rdfs:subClassOf, rdfs:subPropertyOf or skos:closeMatch).
         A property with no public parent says so (relation `none`).
  DROP   a public term covers it. ns.ttl marks it owl:deprecated and names the
         replacement with dcterms:isReplacedBy. Preference: W3C Recommendation,
         then schema.org, then another public vocabulary.
  INFRA  homelab- or tool-specific. Deprecated with a comment and no public
         replacement; it stays in the private ontology it came from.

Nothing is deleted: a published IRI keeps resolving and carries a pointer
instead of a 404. Alignments live in their own file because rdfs:subClassOf is
inferential; loading it changes what a store's type queries return, so a
consumer opts in. The deprecation annotations in ns.ttl infer nothing.

    uv run --script scripts/trim.py --write      # apply the tables to ns.ttl, ns.html, alignments.ttl
    uv run --script scripts/trim.py --selftest   # validate, then prove every rule rejects a mutant
"""

import argparse
import csv
import re
import shutil
import sys
import tempfile
from pathlib import Path

from rdflib import OWL, RDF, RDFS, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, SKOS

ROOT = Path(__file__).resolve().parent.parent
NAMESPACE = "https://scbrown.github.io/quechua/ns#"
TABLES = ("trim/classes.tsv", "trim/properties.tsv")
DECISIONS = {"KEEP", "DROP", "INFRA"}
RELATIONS = {
    "subClassOf": RDFS.subClassOf,
    "subPropertyOf": RDFS.subPropertyOf,
    "closeMatch": SKOS.closeMatch,
}
INFRA_COMMENT = (
    "Deprecated: homelab- or tool-specific, outside the public profile. "
    "No public replacement; it remains in the private ontology it came from."
)
# Always-available W3C core vocabularies; every other prefix must be pinned.
BUILTIN = {
    "rdf": (str(RDF), {str(RDF.Property)}),
    "rdfs": (str(RDFS), {str(RDFS.isDefinedBy)}),
}


def pinned(root: Path) -> dict[str, tuple[str, set[str]]]:
    """prefix -> (namespace, defined IRIs), from vocab/SOURCES.tsv and the term lists."""
    out = dict(BUILTIN)
    with (root / "vocab/SOURCES.tsv").open() as handle:
        rows = csv.DictReader((line for line in handle if not line.startswith("#")), delimiter="\t")
        for row in rows:
            listed = (root / "vocab" / f"{row['name']}.terms").read_text().split()
            out[row["prefix"]] = (row["namespace"], set(listed))
    return out


def tables(root: Path) -> dict[str, dict]:
    """term -> its row. Refuses a malformed row or a term decided twice."""
    rows: dict[str, dict] = {}
    for table in TABLES:
        kind = "class" if "classes" in table else "property"
        with (root / table).open() as handle:
            for number, line in enumerate(handle, 1):
                if line.startswith("#") or not line.strip():
                    continue
                cells = line.rstrip("\n").split("\t")
                if len(cells) != 5:
                    raise ValueError(f"{table}:{number}: expected 5 tab-separated cells, got {len(cells)}")
                term, decision, relation, target, note = cells
                if term in rows:
                    raise ValueError(f"{table}:{number}: {term} is decided twice")
                rows[term] = {"kind": kind, "decision": decision, "relation": relation,
                              "target": target, "note": note, "where": f"{table}:{number}"}
    return rows


def resolve(target: str, vocab: dict) -> URIRef:
    """A prefixed target as an IRI that a pinned vocabulary defines, or a local Quechua term."""
    if ":" not in target:
        return URIRef(NAMESPACE + target)
    prefix, local = target.split(":", 1)
    if prefix not in vocab:
        raise ValueError(f"{target}: prefix {prefix!r} is not pinned in vocab/SOURCES.tsv")
    namespace, defined = vocab[prefix]
    iri = namespace + local
    if iri not in defined:
        raise ValueError(f"{target}: {iri} is not defined by the pinned {prefix} vocabulary")
    return URIRef(iri)


def check_rows(rows: dict, declared: set[str], vocab: dict) -> None:
    """M1-M4 on the tables alone: coverage, decisions, and every target real."""
    missing, extra = declared - set(rows), set(rows) - declared
    if missing or extra:
        raise ValueError(f"trim tables differ from the catalog: undecided {sorted(missing)[:5]}, unknown {sorted(extra)[:5]}")
    for term, row in rows.items():
        where, decision, relation, target = row["where"], row["decision"], row["relation"], row["target"]
        if decision not in DECISIONS:
            raise ValueError(f"{where}: unknown decision {decision!r}")
        if decision == "DROP":
            if relation != "isReplacedBy" or ":" not in target:
                raise ValueError(f"{where}: DROP {term} needs isReplacedBy and a public target")
            resolve(target, vocab)
        elif decision == "INFRA":
            if relation or target:
                raise ValueError(f"{where}: INFRA {term} carries no replacement")
        else:
            if relation == "none":
                if row["kind"] != "property" or target:
                    raise ValueError(f"{where}: only a property may KEEP with no public parent")
                continue
            if relation not in RELATIONS or not target:
                raise ValueError(f"{where}: KEEP {term} needs subClassOf/subPropertyOf/closeMatch and a target")
            parent = resolve(target, vocab)
            if str(parent).startswith(NAMESPACE):
                local = str(parent)[len(NAMESPACE):]
                if rows.get(local, {}).get("decision") != "KEEP":
                    raise ValueError(f"{where}: KEEP {term} aligns to {local}, which is not kept")
    for term, row in rows.items():  # every kept class reaches a public parent
        if row["kind"] != "class" or row["decision"] != "KEEP":
            continue
        seen, current = set(), term
        while ":" not in rows[current]["target"]:
            if current in seen:
                raise ValueError(f"{row['where']}: KEEP {term} aligns in a cycle")
            seen.add(current)
            current = rows[current]["target"]
        if row["decision"] == "KEEP" and not rows[current]["target"]:
            raise ValueError(f"{row['where']}: KEEP {term} never reaches a public term")


def expected(rows: dict, vocab: dict) -> tuple[Graph, Graph]:
    """The deprecation annotations ns.ttl must carry, and the alignments graph."""
    notes, align = Graph(), Graph()
    for term, row in rows.items():
        subject = URIRef(NAMESPACE + term)
        if row["decision"] == "DROP":
            notes.add((subject, OWL.deprecated, Literal(True)))
            notes.add((subject, DCTERMS.isReplacedBy, resolve(row["target"], vocab)))
        elif row["decision"] == "INFRA":
            notes.add((subject, OWL.deprecated, Literal(True)))
            notes.add((subject, RDFS.comment, Literal(INFRA_COMMENT)))
        elif row["relation"] in RELATIONS:
            align.add((subject, RELATIONS[row["relation"]], resolve(row["target"], vocab)))
    return notes, align


def validate(root: Path) -> tuple[int, int, int]:
    """M1-M5 against the published files. Returns (kept, dropped, infra)."""
    vocab = pinned(root)
    rows = tables(root)
    catalog = Graph().parse(root / "ns.ttl")
    declared = {str(s)[len(NAMESPACE):] for s in catalog.subjects(RDF.type, None) if str(s).startswith(NAMESPACE)}
    check_rows(rows, declared, vocab)  # also M5: every table term (the v0.4.0 catalog) is still declared
    notes, align = expected(rows, vocab)
    actual = Graph()
    for triple in catalog.triples((None, None, None)):
        if triple[1] in (OWL.deprecated, DCTERMS.isReplacedBy, RDFS.comment):
            actual.add(triple)
    if set(actual) != set(notes):
        raise ValueError(
            f"ns.ttl deprecations differ from the trim tables: {len(set(notes) - set(actual))} missing, "
            f"{len(set(actual) - set(notes))} unexpected; run scripts/trim.py --write"
        )
    published = Graph().parse(root / "alignments.ttl")
    if set(published) != set(align):
        raise ValueError("alignments.ttl differs from the trim tables; run scripts/trim.py --write")
    html = (root / "ns.html").read_text()
    for term, row in rows.items():
        item = re.search(rf'<li id="{re.escape(term)}">(.*?)</li>', html)
        if not item:
            raise ValueError(f"ns.html has no entry for {term}")
        if ("deprecated" in item.group(1)) != (row["decision"] != "KEEP"):
            raise ValueError(f"ns.html deprecation marker for {term} differs from its decision")
    counts = {d: sum(r["decision"] == d for r in rows.values()) for d in DECISIONS}
    return counts["KEEP"], counts["DROP"], counts["INFRA"]


def write(root: Path) -> None:
    """Apply the tables: annotate ns.ttl, mark ns.html, regenerate alignments.ttl."""
    vocab = pinned(root)
    rows = tables(root)
    text = (root / "ns.ttl").read_text()
    if "@prefix dcterms:" not in text:
        text = text.replace("@prefix owl:", "@prefix dcterms: <http://purl.org/dc/terms/> .\n@prefix owl:", 1)
    lines = []
    for line in text.split("\n"):
        match = re.match(rf'^<{re.escape(NAMESPACE)}([^>]+)> a (rdfs:Class|rdf:Property) ; rdfs:label "[^"]*"', line)
        if match and match.group(1) in rows:
            line = line[: match.end()]
            row = rows[match.group(1)]
            if row["decision"] == "DROP":
                line += f' ; owl:deprecated true ; dcterms:isReplacedBy <{resolve(row["target"], vocab)}>'
            elif row["decision"] == "INFRA":
                line += f' ; owl:deprecated true ; rdfs:comment "{INFRA_COMMENT}"'
            line += " ."
        lines.append(line)
    (root / "ns.ttl").write_text("\n".join(lines))

    html = (root / "ns.html").read_text()

    def mark(match: re.Match) -> str:
        term, kind = match.group(1), match.group(2)
        row = rows[term]
        tail = ""
        if row["decision"] == "DROP":
            iri = resolve(row["target"], vocab)
            tail = f' — deprecated, use <a href="{iri}">{row["target"]}</a>'
        elif row["decision"] == "INFRA":
            tail = " — deprecated, homelab-specific"
        return f'<li id="{term}"><code>quechua:{term}</code> — {kind}{tail}</li>'

    html = re.sub(r'<li id="([^"]+)"><code>quechua:[^<]+</code> — (class|property)[^<]*(?:<a [^>]*>[^<]*</a>)?</li>', mark, html)
    (root / "ns.html").write_text(html)

    _, align = expected(rows, vocab)
    align.bind("quechua", NAMESPACE)
    align.bind("skos", str(SKOS))
    for prefix, (namespace, _) in vocab.items():
        align.bind(prefix, namespace)
    header = (
        "# Alignments of the kept Quechua terms to public vocabularies. Generated from\n"
        "# trim/*.tsv by scripts/trim.py; do not edit by hand. rdfs:subClassOf is\n"
        "# inferential, which is why this is a separate file: loading it is opt-in.\n"
    )
    (root / "alignments.ttl").write_text(header + align.serialize(format="turtle"))


def selftest(root: Path) -> None:
    """Every rule must reject a copy that breaks it."""
    files = ("ns.ttl", "ns.html", "alignments.ttl", *TABLES)
    first_drop = next(
        line for line in (root / "trim/classes.tsv").read_text().split("\n") if "\tDROP\t" in line
    )
    mutations = (
        ("undecided term", "trim/classes.tsv", lambda t: t.replace(first_drop + "\n", "", 1)),
        ("decided twice", "trim/properties.tsv", lambda t: t + "name\tDROP\tisReplacedBy\tschema:name\t\n"),
        ("unknown decision", "trim/classes.tsv", lambda t: t.replace("\tDROP\t", "\tMAYBE\t", 1)),
        ("target not in pinned vocabulary", "trim/classes.tsv",
         lambda t: t.replace("schema:Action", "schema:ActionTypo", 1)),
        ("unpinned prefix", "trim/classes.tsv", lambda t: t.replace("schema:Person", "foaf:Person", 1)),
        ("INFRA with a replacement", "trim/classes.tsv",
         lambda t: re.sub(r"^(Host)\tINFRA\t\t", r"\1\tINFRA\tisReplacedBy\tschema:Place", t, count=1, flags=re.M)),
        ("class KEEP with no parent", "trim/classes.tsv",
         lambda t: re.sub(r"^(Verdict\tKEEP)\tsubClassOf\tprov:Entity", r"\1\tnone\t", t, count=1, flags=re.M)),
        ("KEEP aligned to a dropped term", "trim/classes.tsv",
         lambda t: t.replace("Verdict\tKEEP\tsubClassOf\tprov:Entity", "Verdict\tKEEP\tsubClassOf\tWorkItem", 1)),
        ("deprecation missing from ns.ttl", "ns.ttl", lambda t: t.replace(" ; owl:deprecated true", "", 1)),
        ("kept term deprecated in ns.ttl", "ns.ttl",
         lambda t: t.replace('rdfs:label "Verdict" .', 'rdfs:label "Verdict" ; owl:deprecated true .', 1)),
        ("wrong replacement", "ns.ttl", lambda t: t.replace("https://schema.org/Action>", "https://schema.org/Thing>", 1)),
        ("deleted term", "ns.ttl", lambda t: re.sub(r'^<[^>]+#APIEndpoint> .*\n', "", t, count=1, flags=re.M)),
        ("stale alignments", "alignments.ttl", lambda t: t.replace("prov:Entity", "prov:Agent", 1)),
        ("unmarked HTML", "ns.html", lambda t: t.replace(" — deprecated, homelab-specific", "", 1)),
    )
    for name, file, mutate in mutations:
        with tempfile.TemporaryDirectory(prefix="quechua-trim-") as scratch:
            target = Path(scratch)
            for source in files:
                (target / source).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root / source, target / source)
            shutil.copytree(root / "vocab", target / "vocab")
            path = target / file
            original = path.read_text()
            changed = mutate(original)
            if changed == original:
                raise ValueError(f"control {name} did not change its fixture")
            path.write_text(changed)
            try:
                validate(target)
            except (ValueError, KeyError):
                print(f"Rejected: {name}")
            else:
                raise ValueError(f"control {name} was accepted")
    print(f"{len(mutations)} trim controls rejected")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true", help="apply the tables before validating")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.write:
        write(args.root)
    kept, dropped, infra = validate(args.root)
    print(f"Trim valid: {kept} kept, {dropped} replaced by public terms, {infra} homelab-specific; "
          "every target is defined by a pinned vocabulary")
    if args.selftest:
        selftest(args.root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
