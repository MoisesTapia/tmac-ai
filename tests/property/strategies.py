"""Hypothesis strategies for TMAC v1.1.0 delta models.

Provides reusable strategies for generating valid instances of:
- PlannedChange
- DeltaFinding
- ThreatRule / CheckCondition
- Resource attribute dicts

Feature: tmac-v1-1-tfplan-delta
Validates: Requirements 7.6
"""

from hypothesis import strategies as st

from tmac.delta.models import ChangeAction, DeltaFinding, PlannedChange
from tmac.models.rule import CheckCondition, ThreatRule

# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

_RESOURCE_TYPES = ["aws_s3_bucket", "aws_security_group", "aws_iam_role"]
_SEVERITIES = ["Critical", "High", "Medium", "Low", "Info"]
_STRIDES = [
    "Spoofing",
    "Tampering",
    "Repudiation",
    "Information Disclosure",
    "Denial of Service",
    "Elevation of Privilege",
]
_CONDITIONS = ["equals", "not_equals", "in", "not_in", "exists", "not_exists"]
_ACL_VALUES = ["private", "public-read", "public-read-write", "authenticated-read"]

# Simple non-empty identifier text (letters + underscores)
_identifier = st.from_regex(r"[a-z][a-z_]{0,15}", fullmatch=True)


# ---------------------------------------------------------------------------
# attributes_strategy — generates AWS-like resource attribute dicts
# ---------------------------------------------------------------------------

def attributes_strategy() -> st.SearchStrategy:
    """Generate dicts of AWS resource attributes suitable for rule evaluation."""
    return st.fixed_dictionaries(
        {},
        optional={
            "acl": st.sampled_from(_ACL_VALUES),
            "bucket": _identifier,
            "versioning_enabled": st.booleans(),
            "logging": st.one_of(st.none(), st.just({"target_bucket": "logs"})),
            "server_side_encryption": st.one_of(st.none(), st.just("AES256")),
            "publicly_accessible": st.booleans(),
            "multi_az": st.booleans(),
            "encrypted": st.booleans(),
        },
    )


# ---------------------------------------------------------------------------
# planned_change_strategy — generates valid PlannedChange instances
# ---------------------------------------------------------------------------

def _before_after_for_action(action: ChangeAction):
    """Return (before_strategy, after_strategy) consistent with the given action."""
    attrs = attributes_strategy()
    if action == ChangeAction.create:
        return st.just(None), attrs
    elif action == ChangeAction.delete:
        return attrs, st.just(None)
    else:  # update or replace
        return attrs, attrs


@st.composite
def planned_change_strategy(draw) -> PlannedChange:
    """Generate a PlannedChange with semantically consistent before/after values."""
    resource_type = draw(st.sampled_from(_RESOURCE_TYPES))
    resource_name = draw(_identifier)
    action = draw(st.sampled_from(list(ChangeAction)))

    before_st, after_st = _before_after_for_action(action)
    before = draw(before_st)
    after = draw(after_st)

    address = f"{resource_type}.{resource_name}"

    return PlannedChange(
        address=address,
        resource_type=resource_type,
        resource_name=resource_name,
        action=action,
        before=before,
        after=after,
    )


# ---------------------------------------------------------------------------
# delta_finding_strategy — generates valid DeltaFinding instances
# ---------------------------------------------------------------------------

@st.composite
def delta_finding_strategy(draw) -> DeltaFinding:
    """Generate a DeltaFinding with all required fields populated."""
    change_action = draw(st.sampled_from(list(ChangeAction)))

    # value_before is None for create; value_after is None for delete
    if change_action == ChangeAction.create:
        value_before = None
        value_after = draw(st.one_of(st.none(), st.text(max_size=50)))
    elif change_action == ChangeAction.delete:
        value_before = draw(st.one_of(st.none(), st.text(max_size=50)))
        value_after = None
    else:
        value_before = draw(st.one_of(st.none(), st.text(max_size=50)))
        value_after = draw(st.one_of(st.none(), st.text(max_size=50)))

    resource_type = draw(st.sampled_from(_RESOURCE_TYPES))
    resource_name = draw(_identifier)

    return DeltaFinding(
        rule_id=draw(st.from_regex(r"TMAC-[A-Z]+-[A-Z0-9]+-\d{3}", fullmatch=True)),
        rule_name=draw(st.text(min_size=1, max_size=60)),
        severity=draw(st.sampled_from(_SEVERITIES)),
        stride=draw(st.sampled_from(_STRIDES)),
        resource_type=resource_type,
        resource_name=resource_name,
        file_path=f"{resource_type}.{resource_name}",
        line_number=draw(st.integers(min_value=0, max_value=9999)),
        matched_attribute=draw(_identifier),
        description=draw(st.text(max_size=200)),
        mitigation=draw(st.text(max_size=200)),
        references=draw(st.lists(st.text(max_size=100), max_size=3)),
        tags=draw(st.lists(_identifier, max_size=5)),
        change_action=change_action,
        changed_attribute=draw(_identifier),
        value_before=value_before,
        value_after=value_after,
    )


# ---------------------------------------------------------------------------
# rule_strategy — generates ThreatRule with valid CheckCondition
# ---------------------------------------------------------------------------

@st.composite
def rule_strategy(draw) -> ThreatRule:
    """Generate a ThreatRule with a valid CheckCondition."""
    condition = draw(st.sampled_from(_CONDITIONS))
    attribute = draw(_identifier)

    if condition in ("exists", "not_exists"):
        values = []
    else:
        values = draw(st.lists(st.sampled_from(_ACL_VALUES), min_size=1, max_size=3))

    check = CheckCondition(attribute=attribute, condition=condition, values=values)

    resource_type = draw(st.sampled_from(_RESOURCE_TYPES))
    rule_id = draw(st.from_regex(r"TMAC-[A-Z]+-[A-Z0-9]+-\d{3}", fullmatch=True))

    return ThreatRule(
        id=rule_id,
        name=draw(st.text(min_size=1, max_size=60)),
        resource_type=resource_type,
        check=check,
        severity=draw(st.sampled_from(_SEVERITIES)),
        stride=draw(st.sampled_from(_STRIDES)),
        description=draw(st.text(max_size=200)),
        mitigation=draw(st.text(max_size=200)),
        references=draw(st.lists(st.text(max_size=100), max_size=3)),
        tags=draw(st.lists(_identifier, max_size=5)),
    )


# ---------------------------------------------------------------------------
# secret_text_strategy — generates a (token, full_text) pair where full_text
# contains token embedded within arbitrary surrounding text (for R4.1, R4.5)
# ---------------------------------------------------------------------------

# Characters allowed in a token: printable non-whitespace ASCII excluding
# characters used in the redaction placeholder (* and -) to keep the test
# straightforward, but tokens can legitimately contain any non-space chars.
# We use letters+digits only to guarantee the placeholder "***REDACTED***"
# never accidentally contains the token.
_TOKEN_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"

_token = st.text(
    alphabet=_TOKEN_ALPHABET,
    min_size=8,
    max_size=64,
)


@st.composite
def secret_text_strategy(draw) -> tuple:
    """Generate (token, full_text) where full_text contains token embedded in arbitrary text.

    Returns:
        A tuple (token: str, full_text: str) where full_text contains token at
        least once as a substring.
    """
    token = draw(_token)

    # Arbitrary surrounding text (may be empty)
    prefix = draw(st.text(max_size=80))
    suffix = draw(st.text(max_size=80))

    full_text = prefix + token + suffix

    return (token, full_text)


# ---------------------------------------------------------------------------
# finding_list_strategy — generates mixed lists of Finding / DeltaFinding
# (for comment formatter property tests, tmac-v1-6-pr-agent)
# ---------------------------------------------------------------------------

from tmac.models.finding import Finding


@st.composite
def finding_strategy(draw) -> Finding:
    """Generate a plain Finding (no change_action)."""
    resource_type = draw(st.sampled_from(_RESOURCE_TYPES))
    resource_name = draw(_identifier)
    return Finding(
        rule_id=draw(st.from_regex(r"TMAC-[A-Z]+-[A-Z0-9]+-\d{3}", fullmatch=True)),
        rule_name=draw(st.text(min_size=1, max_size=60)),
        severity=draw(st.sampled_from(_SEVERITIES)),
        stride=draw(st.sampled_from(_STRIDES)),
        resource_type=resource_type,
        resource_name=resource_name,
        file_path=f"{resource_type}.{resource_name}",
        line_number=draw(st.integers(min_value=0, max_value=9999)),
        matched_attribute=draw(_identifier),
        description=draw(st.text(max_size=200)),
        mitigation=draw(st.text(max_size=200)),
        references=draw(st.lists(st.text(max_size=100), max_size=3)),
        tags=draw(st.lists(_identifier, max_size=5)),
    )


@st.composite
def finding_list_strategy(draw) -> list:
    """Generate a list of Finding and/or DeltaFinding instances."""
    n = draw(st.integers(min_value=0, max_value=8))
    findings = []
    for _ in range(n):
        use_delta = draw(st.booleans())
        if use_delta:
            findings.append(draw(delta_finding_strategy()))
        else:
            findings.append(draw(finding_strategy()))
    return findings


# ---------------------------------------------------------------------------
# comment_context_strategy — generates CommentContext with varying fields
# (for comment formatter property tests, tmac-v1-6-pr-agent)
# ---------------------------------------------------------------------------

from tmac.ci.comment import CommentContext

_FAIL_ON_VALUES = ["critical", "high", "medium", "low", "info"]

# artifact_ref: a short printable ASCII string (URL-like but kept simple)
_artifact_ref = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/_.-:",
    min_size=1,
    max_size=80,
)


@st.composite
def comment_context_strategy(draw) -> CommentContext:
    """Generate a CommentContext with varying fail_on, max_length, artifact_ref.

    max_length is always at least as large as the maximum possible minimum body:
    the skeleton with 0 rows AND the truncation notice for up to 10 findings
    (the maximum generated by finding_list_strategy). This ensures the truncation
    budget can always be satisfied (the spec only guarantees the budget is met when
    a 0-row body including the truncation notice fits within the limit).
    """
    fail_on = draw(st.sampled_from(_FAIL_ON_VALUES))
    artifact_ref = draw(_artifact_ref)
    introduced = draw(st.integers(min_value=0, max_value=50))
    resolved = draw(st.integers(min_value=0, max_value=50))

    # Compute the minimum body size: 0 rows with the maximum possible truncation
    # notice (using 10 as an upper bound for the count).  This is the absolute
    # minimum body the formatter can produce when it has to drop all rows.
    from tmac.ci.comment import CommentContext as _CC, CommentFormatter as _CF
    _probe_ctx = _CC(
        fail_on=fail_on,
        artifact_ref=artifact_ref,
        max_length=65536,
        introduced=introduced,
        resolved=resolved,
    )
    # Probe with the maximum omitted count we might generate (10) to get the
    # worst-case minimum skeleton length.
    min_skeleton = len(_CF()._render_body([], _probe_ctx, omitted=10))

    # Allow some variety: sometimes tight (skeleton + small buffer), sometimes roomy
    max_length = draw(st.integers(min_value=min_skeleton, max_value=min_skeleton + 8192))

    return _CC(
        fail_on=fail_on,
        artifact_ref=artifact_ref,
        max_length=max_length,
        introduced=introduced,
        resolved=resolved,
    )


# ---------------------------------------------------------------------------
# FakeHttpTransport — injectable fake for publisher tests (tmac-v1-6-pr-agent)
# ---------------------------------------------------------------------------

from tmac.ci.publisher import CIContext, HttpResponse, HttpTransport


class FakeHttpTransport:
    """In-memory fake transport that records requests and returns pre-configured responses.

    Usage::

        transport = FakeHttpTransport()
        # Pre-populate with existing comments
        transport.set_list_response([{"id": 1, "body": "some text"}])
        # Route write responses
        transport.set_write_response(201, '{"id": 2}')

        publisher = GitHubCommentPublisher(transport, "test-token")
        publisher.publish(ctx, "body text")

        # Inspect recorded calls
        assert len(transport.written_calls) == 1
    """

    def __init__(self) -> None:
        # List of raw comment dicts to return on GET
        self._list_responses: list[dict] = []
        # Status code to return on write operations (POST/PATCH/PUT)
        self._write_status: int = 201
        self._write_body: str = '{"id": 99}'
        # Record of all calls: list of (method, url, headers, body)
        self.calls: list[tuple] = []
        # Convenience views
        self.written_calls: list[tuple] = []
        self.read_calls: list[tuple] = []
        # Optional: force GET to return 403 to simulate read-only token
        self._get_403: bool = False

    def set_list_response(self, comments: list[dict]) -> None:
        """Set the list of comment/note dicts returned on GET."""
        self._list_responses = list(comments)

    def set_write_response(self, status: int = 201, body: str = '{"id": 99}') -> None:
        """Configure the response returned for write operations."""
        self._write_status = status
        self._write_body = body

    def set_get_403(self, value: bool = True) -> None:
        """Force all GET requests to return 403 (simulate read-only token)."""
        self._get_403 = value

    def request(
        self,
        method: str,
        url: str,
        headers: dict,
        body: "bytes | None",
    ) -> HttpResponse:
        import json as _json

        call = (method, url, headers, body)
        self.calls.append(call)

        if method == "GET":
            self.read_calls.append(call)
            if self._get_403:
                return HttpResponse(status=403, body='{"message":"Forbidden"}')
            return HttpResponse(
                status=200,
                body=_json.dumps(self._list_responses),
            )
        else:
            self.written_calls.append(call)
            return HttpResponse(status=self._write_status, body=self._write_body)


# ---------------------------------------------------------------------------
# existing_comments_strategy — lists of comments with/without the MARKER
# ---------------------------------------------------------------------------

from tmac.ci.comment import MARKER as _MARKER


@st.composite
def existing_comments_strategy(draw) -> list[dict]:
    """Generate a list of comment/note dicts with varying MARKER presence.

    Each comment is a dict with 'id' (unique int) and 'body' (str).
    The list simulates what the platform API would return sorted ascending by
    creation time, so the *last* element is the most recently created.

    Produces:
    - 0..4 comments without MARKER
    - 0..3 comments with MARKER (may be 0 → "no existing marked comment" case)
    Comments are interleaved in arbitrary order.
    """
    n_unmarked = draw(st.integers(min_value=0, max_value=4))
    n_marked = draw(st.integers(min_value=0, max_value=3))
    total = n_unmarked + n_marked

    if total == 0:
        return []

    # Generate unique ids
    ids = list(range(1, total + 1))
    # Shuffle to vary creation order (marked and unmarked interleaved)
    order = draw(st.permutations(list(range(total))))

    # Assign is_marked flags: first n_marked slots are marked
    is_marked_flags = [True] * n_marked + [False] * n_unmarked

    # Build comment dicts in the permuted order (simulating ascending created_at)
    comments = []
    for slot_index in order:
        is_marked = is_marked_flags[slot_index]
        comment_id = ids[slot_index]
        if is_marked:
            body = draw(st.text(max_size=50)) + _MARKER + draw(st.text(max_size=50))
        else:
            body_text = draw(st.text(max_size=80))
            # Ensure it does NOT contain the marker
            body = body_text.replace(_MARKER, "")
        comments.append({"id": comment_id, "body": body})

    return comments


# ---------------------------------------------------------------------------
# ci_context_strategy — generates a valid CIContext for publisher tests
# ---------------------------------------------------------------------------

@st.composite
def ci_context_strategy(draw) -> CIContext:
    """Generate a valid CIContext with a PR number set."""
    platform = draw(st.sampled_from(["github", "gitlab"]))
    pr_number = str(draw(st.integers(min_value=1, max_value=9999)))
    return CIContext(
        platform=platform,
        repo="owner/repo",
        pr_number=pr_number,
        base_ref="main",
        head_ref="feature-branch",
        api_base="https://api.example.com",
        artifact_path="tmac-report.md",
    )
