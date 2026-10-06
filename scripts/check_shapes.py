# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rdflib==7.1.4",
#     "pyshacl==0.30.1",
# ]
# ///
"""Validate the published SHACL shapes against the catalog and their examples."""

import argparse
import re
import tempfile
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, RDFS, SH, XSD, Graph, Literal, URIRef
from rdflib.namespace import Namespace

NAMESPACE = "https://scbrown.github.io/quechua/ns#"
Q = Namespace(NAMESPACE)
EX = Namespace("https://example.org/tracker/")
REC = Namespace("https://example.org/records/")
OG = Namespace("https://example.org/graph/")
# The Quipu engine's own namespace, for its derivation properties.
QUIPU = Namespace("http://quipu.dev/ontology/")
ALLOWED = (NAMESPACE, str(SH), str(RDF), str(RDFS), str(XSD), str(QUIPU))
# Public shapes must not carry private infrastructure names.
FORBIDDEN = re.compile(
    r"\.(lan|svc|local|internal)\b|\b(10|192\.168|172\.(1[6-9]|2\d|3[01]))\.\d+\.\d+",
    re.IGNORECASE,
)

# Each case removes or replaces ONE triple of the valid example and names the
# constraint that must report it. A case that conforms, or fails somewhere
# else, is a broken shape or a broken example.
WORK_ITEM = "work-item-valid.ttl"
CAMAYOC = "camayoc-valid.ttl"
ONTOLOGY = "ontology-valid.ttl"
_WORK_ITEM_CASES = (
    (
        "missing-sourceKind",
        (EX["item-1"], Q.sourceKind, Literal("observed")),
        None,
        Q.sourceKind,
    ),
    (
        "unknown-sourceKind",
        (EX["item-1"], Q.sourceKind, Literal("observed")),
        (EX["item-1"], Q.sourceKind, Literal("guessed")),
        Q.sourceKind,
    ),
    (
        "in-progress-outcome",
        (EX["item-2"], Q.outcome, Literal("done")),
        (EX["item-2"], Q.outcome, Literal("in progress")),
        Q.outcome,
    ),
    (
        "missing-label",
        (EX["item-2"], RDFS.label, Literal("Review the shapes")),
        None,
        RDFS.label,
    ),
    (
        "blockedOn-unresolvable",
        (EX["item-1"], Q.blockedOn, EX["item-2"]),
        (EX["item-1"], Q.blockedOn, EX["run-1"]),
        Q.blockedOn,
    ),
    (
        "read-is-not-grantable",
        (EX["item-1"], Q.grantsAction, Literal("edit")),
        (EX["item-1"], Q.grantsAction, Literal("read")),
        Q.grantsAction,
    ),
    (
        "touchesRepo-string",
        (EX["item-1"], Q.touchesRepo, EX["repo-vocabulary"]),
        (EX["item-1"], Q.touchesRepo, Literal("vocabulary")),
        Q.touchesRepo,
    ),
    (
        "blocker-without-evidence",
        (EX["pr-blocker"], Q.blockerEvidence, Literal("stated")),
        None,
        Q.blockerEvidence,
    ),
    (
        "kinded-blocker-without-probe",
        (EX["pr-blocker"], Q.prRef, Literal("example/vocabulary#4")),
        None,
        None,
    ),
    (
        "observation-without-value",
        (EX["obs-1"], Q.observedValue, Literal("open")),
        None,
        Q.observedValue,
    ),
    (
        "observedBlockedOn-literal",
        (EX["obs-1"], Q.observedBlockedOn, EX["item-2"]),
        (EX["obs-1"], Q.observedBlockedOn, Literal("item-2")),
        Q.observedBlockedOn,
    ),
)
CASES = tuple((WORK_ITEM, *case) for case in _WORK_ITEM_CASES)

CAMAYOC_CASES = (
    (
        CAMAYOC,
        "decision-without-chose",
        (REC["decision-1"], Q.chose, Literal("one file per shape family")),
        None,
        Q.chose,
    ),
    (
        CAMAYOC,
        "review-age-in-months",
        (REC["decision-1"], Q.maxAge, Literal("P12W")),
        (REC["decision-1"], Q.maxAge, Literal("P3M")),
        Q.maxAge,
    ),
    (
        CAMAYOC,
        "verification-without-falsifier",
        (REC["verify-2"], Q.falsifier, Literal("the mutated file still matches")),
        None,
        Q.falsifier,
    ),
    (
        CAMAYOC,
        "adversarial-proof-not-verification",
        (REC["verify-1"], Q.adversariallyProvenBy, REC["verify-2"]),
        (REC["verify-1"], Q.adversariallyProvenBy, REC["step-1"]),
        Q.adversariallyProvenBy,
    ),
    (
        CAMAYOC,
        "execution-path-without-refresh",
        (REC["path-1"], Q.refreshedBy, REC["pages-build"]),
        None,
        Q.refreshedBy,
    ),
    (
        CAMAYOC,
        "metric-without-derivation",
        (REC["metric-1"], QUIPU.derivedBy, REC["derivation-1"]),
        None,
        QUIPU.derivedBy,
    ),
    (
        CAMAYOC,
        "derivation-without-query",
        (
            REC["derivation-1"],
            QUIPU.derivationQuery,
            Literal("avg_over_time(probe_success[7d])"),
        ),
        None,
        QUIPU.derivationQuery,
    ),
    (
        CAMAYOC,
        "step-without-trajectory",
        (REC["step-1"], Q.stepOf, REC["trajectory-1"]),
        None,
        Q.stepOf,
    ),
    (
        CAMAYOC,
        "golden-path-without-exemplar",
        (REC["golden-1"], Q.prunedFrom, REC["trajectory-1"]),
        None,
        Q.prunedFrom,
    ),
    (
        CAMAYOC,
        "omission-without-authority",
        (REC["omission-1"], Q.omissionAuthority, Literal("human-decision")),
        (REC["omission-1"], Q.omissionAuthority, Literal("someone")),
        Q.omissionAuthority,
    ),
    (
        CAMAYOC,
        "promotion-to-verified",
        (REC["promotion-1"], Q.blessingLevel, Literal("advisory")),
        (REC["promotion-1"], Q.blessingLevel, Literal("verified")),
        Q.blessingLevel,
    ),
    (
        CAMAYOC,
        "declared-session",
        (REC["session-1"], Q.sourceKind, Literal("observed")),
        (REC["session-1"], Q.sourceKind, Literal("declared")),
        Q.sourceKind,
    ),
    (
        CAMAYOC,
        "usage-count-as-string",
        (REC["usage-1"], Q.tokensConsumed, Literal(1200)),
        (REC["usage-1"], Q.tokensConsumed, Literal("1200")),
        Q.tokensConsumed,
    ),
    (
        CAMAYOC,
        "usage-without-session",
        (REC["usage-1"], Q.inSession, REC["session-1"]),
        None,
        Q.inSession,
    ),
    (
        CAMAYOC,
        "owner-as-string",
        (REC["metric-1"], Q.ownedBy, REC["alice"]),
        (REC["metric-1"], Q.ownedBy, Literal("alice")),
        Q.ownedBy,
    ),
)


ONTOLOGY_CASES = (
    (
        ONTOLOGY,
        "untraced-directive",
        (OG["directive-1"], Q.trackedBy, OG["task-1"]),
        None,
        None,
    ),
    (
        ONTOLOGY,
        "credential-unknown-status",
        (OG["token-1"], Q.status, Literal("active")),
        (OG["token-1"], Q.status, Literal("expired")),
        Q.status,
    ),
    (
        ONTOLOGY,
        "credential-free-text-expiry",
        (OG["token-1"], Q.expiresAt, Literal("2027-01-01T00:00:00Z")),
        (OG["token-1"], Q.expiresAt, Literal("next year")),
        Q.expiresAt,
    ),
    (
        ONTOLOGY,
        "credential-held-on-non-host",
        (OG["token-1"], Q.heldOn, OG["host-1"]),
        (OG["token-1"], Q.heldOn, OG["policy-1"]),
        Q.heldOn,
    ),
    (
        ONTOLOGY,
        "verification-unknown-result",
        (OG["check-1"], Q.result, Literal("works")),
        (OG["check-1"], Q.result, Literal("maybe")),
        Q.result,
    ),
    (
        ONTOLOGY,
        "verification-free-text-time",
        (OG["check-1"], Q.verifiedAt, Literal("2026-10-07T00:00:00Z")),
        (OG["check-1"], Q.verifiedAt, Literal("yesterday")),
        Q.verifiedAt,
    ),
    (
        ONTOLOGY,
        "collection-negative-count",
        (OG["games"], Q.fileCount, Literal(12)),
        (OG["games"], Q.fileCount, Literal(-1)),
        Q.fileCount,
    ),
    (
        ONTOLOGY,
        "collection-uppercase-extension",
        (OG["cartridges"], Q.hasExtension, Literal(".z64")),
        (OG["cartridges"], Q.hasExtension, Literal(".Z64")),
        Q.hasExtension,
    ),
    (
        ONTOLOGY,
        "collection-parent-not-collection",
        (OG["cartridges"], Q.parentCollection, OG["games"]),
        (OG["cartridges"], Q.parentCollection, OG["share-1"]),
        Q.parentCollection,
    ),
    (
        ONTOLOGY,
        "collection-date-only-mtime",
        (OG["cartridges"], Q.newestMtime, Literal("2026-09-27T12:00:00Z")),
        (OG["cartridges"], Q.newestMtime, Literal("2026-09-27")),
        Q.newestMtime,
    ),
    (
        ONTOLOGY,
        "collection-without-label",
        (OG["games"], RDFS.label, Literal("games")),
        None,
        RDFS.label,
    ),
)


def load_catalog(root: Path) -> tuple[set, set]:
    graph = Graph().parse(root / "ns.ttl")
    classes = {s for s in graph.subjects(RDF.type, RDFS.Class)}
    properties = {s for s in graph.subjects(RDF.type, RDF.Property)}
    return classes, properties


def check_terms(path: Path, shapes: Graph, classes: set, properties: set) -> None:
    """Every IRI is in an allowed namespace and every Quechua term is declared."""
    text = path.read_text()
    if match := FORBIDDEN.search(text):
        raise ValueError(f"{path.name}: private name {match.group(0)!r}")
    shape_names = set(shapes.subjects(RDF.type, SH.NodeShape))
    for triple in shapes:
        for term in triple:
            if isinstance(term, URIRef) and not str(term).startswith(ALLOWED):
                raise ValueError(
                    f"{path.name}: IRI outside the allowed namespaces: {term}"
                )
    for cls in set(shapes.objects(None, SH.targetClass)) | set(
        shapes.objects(None, SH["class"])
    ):
        if cls not in classes:
            raise ValueError(f"{path.name}: class not declared in ns.ttl: {cls}")
    for prop in set(shapes.objects(None, SH.path)) | set(
        shapes.objects(None, SH.targetSubjectsOf)
    ):
        if str(prop).startswith(NAMESPACE) and prop not in properties:
            raise ValueError(f"{path.name}: property not declared in ns.ttl: {prop}")
    for shape in shape_names:
        if not str(shape).startswith(NAMESPACE):
            raise ValueError(f"{path.name}: shape outside the namespace: {shape}")


def report(shapes: Graph, data: Graph) -> tuple[bool, set]:
    conforms, results, _ = validate(data, shacl_graph=shapes, advanced=False)
    paths = set(results.objects(None, SH.resultPath))
    return conforms, paths


def check_examples(shapes: Graph, examples: Path) -> int:
    valid = {}
    for path in sorted(examples.glob("*.ttl")):
        graph = Graph().parse(path)
        conforms, paths = report(shapes, graph)
        if not conforms:
            raise ValueError(f"{path.name} does not conform: {sorted(paths)}")
        valid[path.name] = graph
    cases = CASES + CAMAYOC_CASES + ONTOLOGY_CASES
    for example, name, remove, add, path in cases:
        base = valid[example]
        if remove not in base:
            raise ValueError(f"case {name}: the triple it removes is not in {example}")
        data = Graph()
        for triple in base:
            data.add(triple)
        data.remove(remove)
        if add:
            data.add(add)
        conforms, paths = report(shapes, data)
        if conforms:
            raise ValueError(f"case {name} conformed")
        if path is not None and path not in paths:
            raise ValueError(f"case {name} failed on {sorted(paths)}, not {path}")
        print(f"Rejected invalid example: {name}")
    return len(valid), len(cases)


def check(root: Path) -> None:
    classes, properties = load_catalog(root)
    shapes = Graph()
    files = sorted((root / "shapes").glob("*.shapes.ttl"))
    if not files:
        raise ValueError("no shapes published")
    for path in files:
        graph = Graph().parse(path)
        check_terms(path, graph, classes, properties)
        shapes += graph
    count = len(set(shapes.subjects(RDF.type, SH.NodeShape)))
    print(
        f"Shapes valid: {len(files)} file(s), {count} node shapes, all terms declared"
    )
    examples, cases = check_examples(shapes, root / "shapes" / "examples")
    print(f"{examples} valid examples conform; {cases} invalid examples rejected")


def selftest(root: Path) -> None:
    """Each mutated shapes file must be refused by the same term check."""
    path = root / "shapes" / "work-item.shapes.ttl"
    classes, properties = load_catalog(root)
    original = path.read_text()
    mutations = (
        (
            "undeclared-class",
            original.replace(
                "sh:targetClass quechua:WorkItem",
                "sh:targetClass quechua:NoSuchClass",
                1,
            ),
        ),
        (
            "undeclared-property",
            original.replace(
                "sh:path quechua:outcome", "sh:path quechua:noSuchProperty", 1
            ),
        ),
        (
            "foreign-iri",
            original.replace(
                "@prefix quechua: <https://scbrown.github.io/quechua/ns#>",
                "@prefix quechua: <https://example.org/private#>",
                1,
            ),
        ),
        ("private-name", original + "\n# deployed on tracker.svc\n"),
    )
    for name, text in mutations:
        if text == original:
            raise ValueError(f"control {name} did not change its fixture")
        with tempfile.TemporaryDirectory(prefix="quechua-shapes-") as tmp:
            scratch = Path(tmp) / path.name
            scratch.write_text(text)
            try:
                check_terms(scratch, Graph().parse(scratch), classes, properties)
            except ValueError:
                print(f"Rejected invalid shapes: {name}")
            else:
                raise ValueError(f"control {name} was accepted")
    print(f"{len(mutations)} invalid-shapes controls rejected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    check(args.root)
    if args.selftest:
        selftest(args.root)
