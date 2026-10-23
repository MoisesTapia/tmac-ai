"""
Property-based tests for CloudFormationParser and the CFN scan pipeline.

Validates: Requirement 23, properties P1-P12 (tmac-v1-2-cloudformation)
"""

import atexit
import json
import shutil
import tempfile
from pathlib import Path

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from tmac.models.finding import Finding
from tmac.parsers.cloudformation import CloudFormationParser
from tmac.scanner import Scanner

SERVICES = Path(__file__).parent.parent / "fixtures" / "cfn" / "services"

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

logical_ids = st.from_regex(r"[A-Z][A-Za-z0-9]{0,15}", fullmatch=True)
resource_types = st.sampled_from(
    [
        "AWS::S3::Bucket",
        "AWS::IAM::Role",
        "AWS::EC2::SecurityGroup",
        "AWS::KMS::Key",
        "AWS::SQS::Queue",
    ]
)
keys = st.from_regex(r"[A-Z][A-Za-z]{0,10}", fullmatch=True)
scalars = st.one_of(
    st.booleans(),
    st.integers(min_value=-(10**6), max_value=10**6),
    st.text(alphabet=st.characters(categories=["L", "N"]), max_size=12),
)
values = st.recursive(
    scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=3), st.dictionaries(keys, children, min_size=2, max_size=3)
    ),
    max_leaves=8,
)
properties = st.dictionaries(keys, values, max_size=4)
intrinsics = st.one_of(
    st.builds(lambda v: f"!Ref {v}", logical_ids),
    st.builds(lambda v: f'!Sub "${{{v}}}-x"', logical_ids),
    st.builds(lambda v: f"!GetAtt {v}.Arn", logical_ids),
    st.builds(lambda v: f"!Join ['-', [!Ref {v}, x]]", logical_ids),
    st.builds(lambda v: f"!If [IsProd, !Ref {v}, x]", logical_ids),
)


@st.composite
def templates(draw):
    ids = draw(st.lists(logical_ids, min_size=0, max_size=6, unique=True))
    return {
        "Resources": {
            i: {"Type": draw(resource_types), "Properties": draw(properties)} for i in ids
        }
    }


def _write(content: str, suffix: str) -> str:
    """Write content to a file in its own fresh directory (so scans see only this file)."""
    directory = tempfile.mkdtemp(prefix="tmac-cfn-")
    atexit.register(shutil.rmtree, directory, ignore_errors=True)
    path = Path(directory) / f"template{suffix}"
    path.write_text(content, encoding="utf-8")
    return str(path)


def _dump(template) -> str:
    return yaml.safe_dump(template, sort_keys=False)


def _key(resources):
    return [(r.name, r.resource_type, r.attributes) for r in resources]


parser = CloudFormationParser()

# ---------------------------------------------------------------------------
# Parser properties
# ---------------------------------------------------------------------------


@settings(max_examples=60)
@given(template=templates())
def test_p1_determinism_and_p4_count(template):
    path = _write(_dump(template), ".yaml")
    first, second = parser.parse_strict(path), parser.parse_strict(path)
    assert first == second
    assert len(first) == len(template["Resources"])


@settings(max_examples=60)
@given(template=templates())
def test_p2_yaml_round_trip(template):
    original = parser.parse_strict(_write(_dump(template), ".yaml"))
    again = parser.parse_strict(_write(parser.serialize_to_yaml(original), ".yaml"))
    assert _key(again) == _key(original)


@settings(max_examples=60)
@given(template=templates())
def test_p3_dict_round_trip(template):
    original = parser.parse_template(template)
    assert _key(parser.parse_template(parser.serialize(original))) == _key(original)


@settings(max_examples=60)
@given(template=templates())
def test_p6_yaml_json_equivalence(template):
    from_yaml = parser.parse_strict(_write(_dump(template), ".yaml"))
    from_json = parser.parse_strict(_write(json.dumps(template), ".json"))
    assert _key(from_yaml) == _key(from_json)


@settings(max_examples=60)
@given(ids=st.lists(logical_ids, min_size=1, max_size=5, unique=True), data=st.data())
def test_p5_intrinsics_never_crash(ids, data):
    lines = ["Resources:"]
    for logical_id in ids:
        lines += [f"  {logical_id}:", "    Type: AWS::S3::Bucket", "    Properties:"]
        for n in range(data.draw(st.integers(min_value=1, max_value=3))):
            lines.append(f"      P{n}: {data.draw(intrinsics)}")
    resources = parser.parse_strict(_write("\n".join(lines) + "\n", ".yaml"))
    assert [r.name for r in resources] == ids


@settings(max_examples=40)
@given(template=templates(), ignored=st.data())
def test_p9_ignore_map_idempotent_and_p11_suppression(template, ignored):
    ids = list(template["Resources"])
    chosen = ignored.draw(st.sets(st.sampled_from(ids))) if ids else set()
    lines = ["Resources:"]
    for logical_id, body in template["Resources"].items():
        if logical_id in chosen:
            lines.append("  # tmac:ignore")
        lines.append(f"  {logical_id}:")
        lines += ["    " + line for line in _dump(body).splitlines()]
    path = _write("\n".join(lines) + "\n", ".yaml")
    assert parser.get_ignore_map(path) == parser.get_ignore_map(path)
    assert set(parser.get_ignore_map(path)) == chosen
    findings = Scanner(parser=parser).run_scan(str(Path(path).parent)).findings
    assert not any(f.resource_name in chosen for f in findings)


# ---------------------------------------------------------------------------
# Pipeline properties (over the service fixtures)
# ---------------------------------------------------------------------------

_SEVERITIES = ["info", "low", "medium", "high", "critical"]


@settings(max_examples=5, deadline=None)
@given(min_severity=st.sampled_from(_SEVERITIES))
def test_p7_statistics_p8_monotonic_p10_findings_p12_prefix(min_severity):
    result = Scanner(parser=parser).run_scan(str(SERVICES), min_severity=min_severity)
    stats = result.statistics
    assert (
        stats.critical + stats.high + stats.medium + stats.low + stats.info
        == len(result.findings)
        == stats.total_findings
    )
    assert all(
        _SEVERITIES.index(f.severity.lower()) >= _SEVERITIES.index(min_severity)
        for f in result.findings
    )
    for finding in result.findings:
        assert finding.rule_id.startswith("TMAC-CFN-")
        assert Finding(**finding.model_dump()) == finding
