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
ALLOWED = (NAMESPACE, str(SH), str(RDF), str(RDFS), str(XSD))
# Public shapes must not carry private infrastructure names.
FORBIDDEN = re.compile(
    r"\.(lan|svc|local|internal)\b|\b(10|192\.168|172\.(1[6-9]|2\d|3[01]))\.\d+\.\d+",
    re.IGNORECASE,
)

# Each case removes or replaces ONE triple of the valid example and names the
# constraint that must report it. A case that conforms, or fails somewhere
# else, is a broken shape or a broken example.
CASES = (
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
    valid = Graph().parse(examples / "work-item-valid.ttl")
    conforms, paths = report(shapes, valid)
    if not conforms:
        raise ValueError(f"the valid example does not conform: {sorted(paths)}")
    for name, remove, add, path in CASES:
        if remove not in valid:
            raise ValueError(
                f"case {name}: the triple it removes is not in the example"
            )
        data = Graph()
        for triple in valid:
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
    return len(CASES)


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
    cases = check_examples(shapes, root / "shapes" / "examples")
    print(f"Valid example conforms; {cases} invalid examples rejected")


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
