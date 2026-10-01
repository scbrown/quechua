# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rdflib==7.1.4",
# ]
# ///
"""Validate the published declaration catalog and prove its failure controls."""

import argparse
import re
import shutil
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from rdflib import OWL, RDF, RDFS, Graph, Literal, URIRef
from rdflib.plugins.parsers.notation3 import BadSyntax

NAMESPACE = "https://scbrown.github.io/quechua/ns#"
# The one non-term subject: the catalog's own ontology header, carrying the
# release version so a consumer can read what it loaded.
ONTOLOGY = URIRef("https://scbrown.github.io/quechua/ns")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
FILES = ("ns.ttl", "ns.html", "index.html", ".nojekyll", "CHANGELOG.md")


def catalog_version(graph: Graph) -> str:
    """The single owl:versionInfo of the ontology header, a plain semver."""
    if set(graph.objects(ONTOLOGY, RDF.type)) != {OWL.Ontology}:
        raise ValueError("missing the owl:Ontology header for the catalog")
    if not set(graph.predicates(ONTOLOGY)) <= {RDF.type, OWL.versionInfo}:
        raise ValueError("unexpected predicate on the ontology header")
    versions = [str(v) for v in graph.objects(ONTOLOGY, OWL.versionInfo)]
    if len(versions) != 1 or not SEMVER.match(versions[0]):
        raise ValueError(f"expected exactly one semver owl:versionInfo, got {versions}")
    return versions[0]


def changelog_section(text: str, version: str) -> str:
    """The body under `## [version]`, up to the next `## [` heading or link refs."""
    heads = list(re.finditer(r"^## \[(?P<v>[^\]]+)\]", text, re.MULTILINE))
    for i, head in enumerate(heads):
        if head.group("v") != version:
            continue
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[head.end() : end].split("\n", 1)[-1]
        return re.split(r"^\[[^\]]+\]: ", body, maxsplit=1, flags=re.MULTILINE)[0].strip()
    return ""


class CatalogHTML(HTMLParser):
    """Read anchors and links without depending on HTML layout or line breaks."""

    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag in ("a", "link"):
            self.links.append(attrs)


def validate_catalog(root: Path) -> tuple[int, int, str]:
    """Reject malformed RDF, foreign terms, missing labels and divergent HTML."""
    for name in FILES:
        if not (root / name).is_file():
            raise ValueError(f"missing publication file: {name}")
    graph = Graph().parse(data=(root / "ns.ttl").read_text(), format="turtle")
    version = catalog_version(graph)
    if not changelog_section((root / "CHANGELOG.md").read_text(), version):
        raise ValueError(f"CHANGELOG.md has no non-empty section for {version}")
    subjects = set(graph.subjects()) - {ONTOLOGY}
    if not subjects:
        raise ValueError("the vocabulary is empty")
    names = set()
    for subject in subjects:
        if not isinstance(subject, URIRef) or not str(subject).startswith(NAMESPACE):
            raise ValueError(f"subject outside the public namespace: {subject}")
        local = str(subject)[len(NAMESPACE) :]
        if not local:
            raise ValueError("empty vocabulary term")
        names.add(local)
        kinds = set(graph.objects(subject, RDF.type))
        if not kinds or not kinds <= {RDFS.Class, RDF.Property}:
            raise ValueError(f"expected a class/property declaration for {subject}")
        if set(graph.objects(subject, RDFS.label)) != {Literal(local)}:
            raise ValueError(f"expected exactly one local-name label for {subject}")
        if not set(graph.predicates(subject)) <= {RDF.type, RDFS.label}:
            raise ValueError(f"unexpected predicate in declaration catalog: {subject}")
    html = CatalogHTML()
    html.feed((root / "ns.html").read_text())
    if len(html.ids) != len(set(html.ids)) or set(html.ids) != names:
        raise ValueError("HTML term anchors differ from the Turtle vocabulary")
    if not any(
        link.get("rel") == "alternate"
        and link.get("type") == "text/turtle"
        and link.get("href") == "ns.ttl"
        for link in html.links
    ):
        raise ValueError("missing Turtle alternate link")
    index = CatalogHTML()
    index.feed((root / "index.html").read_text())
    if not {"ns", "ns.ttl"} <= {link.get("href") for link in index.links}:
        raise ValueError("index must link to both catalogs")
    return len(subjects), len(graph), version


def selftest(root: Path) -> None:
    """Mutate disposable copies; every bad catalog must fail the same validator."""
    mutations = (
        ("empty", "ns.ttl", lambda _: ""),
        (
            "no-version",
            "ns.ttl",
            lambda text: text.replace(' ; owl:versionInfo "', ' ; rdfs:comment "'),
        ),
        (
            "two-versions",
            "ns.ttl",
            lambda text: text.replace(
                'owl:versionInfo "', 'owl:versionInfo "9.9.9", "', 1
            ),
        ),
        (
            "no-changelog-section",
            "CHANGELOG.md",
            lambda text: re.sub(r"^## \[\d+\.\d+\.\d+\]", "## [old]", text, flags=re.MULTILINE),
        ),
        ("syntax", "ns.ttl", lambda text: text + "\n<unterminated"),
        (
            "foreign",
            "ns.ttl",
            lambda text: text.replace(NAMESPACE, "https://example.org/foreign#"),
        ),
        ("label", "ns.ttl", lambda text: text.replace('"APIEndpoint"', '"wrong"')),
        (
            "anchors",
            "ns.html",
            lambda text: text.replace('id="APIEndpoint"', 'id="absent"'),
        ),
        (
            "alternate",
            "ns.html",
            lambda text: text.replace('rel="alternate"', 'rel="other"'),
        ),
    )
    for name, file, mutate in mutations:
        with tempfile.TemporaryDirectory(prefix="quechua-catalog-") as scratch:
            target = Path(scratch)
            for source in FILES:
                shutil.copy2(root / source, target / source)
            path = target / file
            original = path.read_text()
            changed = mutate(original)
            if changed == original:
                raise ValueError(f"control {name} did not change its fixture")
            path.write_text(changed)
            try:
                validate_catalog(target)
            except (ValueError, BadSyntax):
                print(f"Rejected invalid catalog: {name}")
            else:
                raise ValueError(f"control {name} was accepted")
    print(f"{len(mutations)} invalid-catalog controls rejected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument(
        "--expect-version",
        help="refuse unless the catalog's owl:versionInfo equals this (a v prefix is ignored)",
    )
    parser.add_argument(
        "--notes",
        type=Path,
        help="write the version's CHANGELOG section here (release notes)",
    )
    args = parser.parse_args()
    terms, triples, version = validate_catalog(args.root)
    print(
        f"Catalog valid: version {version}, {terms} terms, {triples} triples; HTML anchors match"
    )
    if args.expect_version is not None and args.expect_version.removeprefix("v") != version:
        raise SystemExit(
            f"REFUSING: tag {args.expect_version} does not match owl:versionInfo {version}"
        )
    if args.notes:
        args.notes.write_text(
            changelog_section((args.root / "CHANGELOG.md").read_text(), version) + "\n"
        )
    if args.selftest:
        selftest(args.root)
