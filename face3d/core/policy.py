"""Consent gates, licence taint and network guard (eth digest sections 2-4, A7, F1-F20).

Conventions: timestamps are ISO-8601 strings (naive = UTC). Gates fail closed:
a missing record, missing scope, expired record, unknown rights or unknown
licence all deny. Values in POLICY are spec constants (WP-04; eth digest A2/A3).
"""
from __future__ import annotations

import contextlib
import enum
import json
import socket
import types
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


class Scope(enum.IntFlag):
    CAPTURE = 1
    RECONSTRUCT = 2
    STORE_RAW = 4
    TEXTURE = 8
    RENDER_PRIVATE = 16
    PUBLISH_NONCOMMERCIAL = 32
    COMMERCIAL = 64
    PRINT_3D = 128
    RIG_ANIMATE = 256
    CLOUD_PROCESSING = 512
    IDENTITY_CHECK = 1024
    AI_TRAINING = 2048


SIGNER_ROLES = ("self", "subject", "guardian", "estate")


@dataclass
class ConsentRecord:
    consent_id: str
    subject_pseudonym: str
    signer_role: str
    consent_text_version: str
    method: str
    signed_at: str
    expires_at: str | None
    jurisdiction_tags: list
    photo_sha256: list
    retention_days: int
    revocation_contact: str
    scopes: Scope
    attested_age: int | None = None
    deceased: bool = False

    def __post_init__(self):
        if self.signer_role not in SIGNER_ROLES:
            raise ValueError(f"signer_role must be one of {SIGNER_ROLES}")
        self.scopes = Scope(int(self.scopes))

    def to_json(self) -> str:
        d = asdict(self)
        d["scopes"] = int(self.scopes)
        return json.dumps(d, sort_keys=True)

    @classmethod
    def from_json(cls, s: str) -> "ConsentRecord":
        d = json.loads(s)
        d["scopes"] = Scope(d["scopes"])
        return cls(**d)


class DataClass(enum.Enum):
    PERSONAL_IMAGE = 1
    BIOMETRIC_GEOMETRY = 2
    BIOMETRIC_TEMPLATE = 3
    LIKENESS_ASSET = 4
    AGGREGATE_PRIOR = 5


@dataclass
class LicenceTag:
    spdx: str
    commercial_ok: bool | None
    redistributable: bool | None
    attribution: str = ""
    share_alike: bool = False
    use_restrictions: tuple = ()
    territory_excluded: tuple = ()
    source: str = ""
    version: str = ""
    sha256: str = ""


def taint(components: list) -> bool:
    """True iff every component is explicitly commercial_ok (None counts as False; fail closed).

    An empty component list means provenance was lost and is NOT clean (False).
    """
    if not components:
        return False
    return all(c.commercial_ok is True for c in components)


POLICY = types.MappingProxyType({
    "min_self_consent_age": 18,
    "cache_ttl_days": 0,
    "max_faces_auto_fitted_per_photo": 1,
    "persist_embeddings": False,
    "network_enabled": False,
    "unknown_commercial_ok": False,
})

# closed enum of rights bases (ethics PhotoRecord); anything else fails closed (F7)
RIGHTS_BASES = frozenset({"self_shot", "subject_selfie", "photographer_licence",
                          "cc_licence", "public_domain"})


@dataclass
class GateResult:
    allowed: bool
    missing: list = field(default_factory=list)
    reasons: list = field(default_factory=list)


# operation -> required scopes (any-of for 'publish')
_REQUIRED = {
    "reconstruct": Scope.RECONSTRUCT,
    "identity_keys": Scope.RECONSTRUCT,
    "expression_keys": Scope.RIG_ANIMATE,
    "texture": Scope.TEXTURE,
    "store_raw": Scope.STORE_RAW,
    "identity_check": Scope.IDENTITY_CHECK,
    "network": Scope.CLOUD_PROCESSING,
    "commercial_export": Scope.COMMERCIAL,
    "print": Scope.PRINT_3D,
    "training": Scope.AI_TRAINING,
}
# Operations a deceased subject's non-estate consent may not authorise (F6): commercial
# tier and the replica tier ranked above it (training, rig/expression export, print).
_COMMERCIAL_OPS = ("commercial_export", "training", "expression_keys", "print")


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def check(operation: str, record: ConsentRecord | None, *, photos_sha256=(), rights_basis=(),
          now: datetime, result_commercial_ok=None, network_enabled=False,
          online_access=False) -> GateResult:
    """Evaluate consent gate for ``operation``; names missing scopes in ``missing``."""
    if operation not in _REQUIRED and operation != "publish":
        raise ValueError(f"unknown operation {operation!r}")
    missing: list = []
    reasons: list = []
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if record is None:
        return GateResult(False, ["consent_record"], ["no consent record (F1)"])

    if operation == "publish":
        if not (record.scopes & (Scope.PUBLISH_NONCOMMERCIAL | Scope.COMMERCIAL)):
            missing += ["PUBLISH_NONCOMMERCIAL", "COMMERCIAL"]
    else:
        need = _REQUIRED[operation]
        if not (record.scopes & need):
            missing.append(need.name)

    try:
        age = record.attested_age
        if age is not None and age < POLICY["min_self_consent_age"] \
                and record.signer_role != "guardian":
            return GateResult(False, missing,
                              ["minor without guardian consent blocks all operations (F5)"])
    except TypeError:
        return GateResult(False, missing, ["malformed attested_age (F5)"])

    try:
        if record.expires_at is not None and _parse(record.expires_at) <= now:
            reasons.append("consent record expired (F3)")
    except (ValueError, TypeError, AttributeError):
        reasons.append("consent expiry unparseable (F3)")

    if operation == "reconstruct":
        known = set(record.photo_sha256)
        bad = [h for h in photos_sha256 if h not in known]
        if bad or not photos_sha256:
            reasons.append("photo sha256 not covered by consent record (F2)")

    if operation in ("texture", "store_raw"):
        if isinstance(rights_basis, (str, bytes)):
            rights_basis = (rights_basis,)
        rb = list(rights_basis) if rights_basis is not None else []
        if not rb or any(not isinstance(r, str) or r not in RIGHTS_BASES for r in rb):
            reasons.append("rights basis unknown or invalid (F7)")

    if operation == "network":
        if not network_enabled:
            reasons.append("network disabled (A7)")
        if not online_access:
            reasons.append("online access not granted (A7)")

    if operation == "commercial_export" and result_commercial_ok is not True:
        reasons.append("result not commercial_ok (licence taint, F8)")

    commercial = operation in _COMMERCIAL_OPS or (
        operation == "publish" and bool(record.scopes & Scope.COMMERCIAL))
    if commercial and record.deceased and record.signer_role != "estate":
        reasons.append("deceased subject: commercial use requires estate consent (F6)")

    return GateResult(not missing and not reasons, missing, reasons)


@contextlib.contextmanager
def network_guard():
    """Block socket connect/connect_ex/sendto/sendmsg, create_connection and
    getaddrinfo with PermissionError (eth A7)."""
    cls_attrs = ("connect", "connect_ex", "sendto", "sendmsg")
    mod_attrs = ("create_connection", "getaddrinfo")
    saved_cls = {n: socket.socket.__dict__.get(n) for n in cls_attrs}
    saved_mod = {n: getattr(socket, n) for n in mod_attrs}

    def _deny(*a, **k):
        raise PermissionError("network disabled by face3d network_guard")

    for n in cls_attrs:
        setattr(socket.socket, n, _deny)
    for n in mod_attrs:
        setattr(socket, n, _deny)
    try:
        yield
    finally:
        for n in cls_attrs:
            if saved_cls[n] is None:
                delattr(socket.socket, n)  # restore inheritance from _socket.socket
            else:
                setattr(socket.socket, n, saved_cls[n])
        for n in mod_attrs:
            setattr(socket, n, saved_mod[n])
