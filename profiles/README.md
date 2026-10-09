# Valid-time projection

`valid-time.json` declares a class-indexed function from source properties to
valid-time boundaries. `scripts/project_valid_time.py` is its offline reference
consumer. Integrations select a named profile explicitly and pass **asserted**
class IRIs and property values; the resolver derives the boundaries automatically.
Loading SHACL or subclass alignments does not select or activate this profile.

| Profile | Class | Start | End |
| --- | --- | --- | --- |
| tracker | schema:Action | schema:dateCreated | schema:endTime |
| activity | schema:Action | schema:startTime | schema:endTime |
| activity | prov:Activity | prov:startedAtTime | prov:endedAtTime |
| calendar | ical:Vevent | ical:dtstart | ical:dtend |
| calendar | ical:Vtodo | ical:dtstart | ical:completed |
| point | sosa:Observation | sosa:resultTime | start + epsilon_ns |

The tracker profile describes the record's lifetime. An Action's execution start
is a different meaning, covered by `activity`. Do not substitute modification time
for creation. A to-do's `due` is a deadline, not its completion boundary; an open
Vtodo has no end. A scheduled event uses its declared end. No generic Quechua
class or timestamp property is introduced. All referenced terms are checked
against the repository's pinned public vocabularies.

Intervals are **[start, end)**. Start is required; an absent end produces JSON
`null` (open-ended). Equal or backwards boundaries refuse; a point uses the
profile's explicit positive integer epsilon, currently one nanosecond. That is
an application indexing policy, not a claim that a physical event lasted 1 ns.
Valid time describes the modeled lifetime, never the transaction that ingested it.
An adapter must apply it only to the facts it intends to qualify: status revisions
and observations of a work item do not all inherit its entire lifetime.

Input property values are lists of lexical timestamp strings, keyed by full IRIs.
A selected start has exactly one value and end zero or one. Quipu typed-literal
objects and prefixed terms must be normalized by the calling adapter; a label
string is not an IRI. No inferred superclass expansion or default class applies.
Multiple declared types with different rules refuse rather than silently choosing
one. Consumers must pin the declaration and select the intended named graph;
this tool neither queries nor writes a store.

Timestamps require RFC3339 date/time and a known offset, with up to nine fractional
digits. Arithmetic uses integer nanoseconds and output normalizes to UTC without
truncation. Leap seconds, floating times, unknown `-00:00` offsets and excess
precision refuse. Date-only values require an explicit IANA `--date-zone`; each
boundary converts its own local midnight so daylight-saving days remain correct.
A nonexistent or ambiguous midnight refuses. Missing end stays open-ended even
for a date-only calendar event; an adapter must supply an explicit end if the
source format implies a duration. Floating local calendar date-times must be
resolved upstream; they are never guessed from the machine's timezone.

Example input:

```json
{
  "types": ["https://schema.org/Action"],
  "properties": {
    "https://schema.org/dateCreated": ["2026-10-07T02:55:21.233261492Z"]
  }
}
```

```sh
uv run --script scripts/project_valid_time.py --profile tracker record.json
python3 -m unittest discover -s tests -v
```

The projection emits
`{"valid_from":"2026-10-07T02:55:21.233261492Z","valid_to":null}`.
Invalid input exits 2 and emits no successful projection. This is an opt-in
reference implementation; it does not change existing producers, serving shapes,
or stored facts. Consumer adoption requires that consumer's own before/after
probe and review. Existing production shape-load holds remain independent.

Standards: [W3C OWL-Time](https://www.w3.org/TR/owl-time/) describes instants and
intervals; [PROV-O](https://www.w3.org/TR/prov-o/) provides activity boundaries;
[W3C RDF Calendar](https://www.w3.org/2002/12/cal/ical#) supplies calendar terms;
[SOSA](https://www.w3.org/TR/vocab-ssn/) supplies observation result time;
[schema.org](https://schema.org/Action) supplies Action lifecycle properties.
These standards provide terms. The half-open convention, named profiles,
null policy and epsilon are the application contract declared here.
