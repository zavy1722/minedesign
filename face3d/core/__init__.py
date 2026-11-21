"""face3d.core: formats, badged defaults, consent and licence policy, stage cache, audit (DESIGN 2.2 L0).

Public re-exports of the modules listed in DESIGN 2.3 (finalised by WP-23).  Every name is importable
from its module path as before; a name that exists in two modules is exported once.
Submodules stay importable as attributes (``from face3d.core import audit``).
"""
from .audit import (AuditLog)
from .cache import (DEFAULT_TTL_DAYS, StageCache)
from .config import (BADGES, UNVERIFIED_BADGES, Default, Namespace, register_defaults, get, load_overrides,
    resolve, unverified_count, snapshot)
from .policy import (Scope, SIGNER_ROLES, ConsentRecord, DataClass, LicenceTag, taint, POLICY, RIGHTS_BASES,
    GateResult, check, network_guard)
from .schema import (FormatError, dump_json, load_json, canonical_json, sha256_bytes, sha256_file,
    save_arrays, load_arrays)

__all__ = [
    'AuditLog', 'BADGES', 'ConsentRecord', 'DEFAULT_TTL_DAYS', 'DataClass', 'Default', 'FormatError',
    'GateResult', 'LicenceTag', 'Namespace', 'POLICY', 'RIGHTS_BASES', 'SIGNER_ROLES', 'Scope',
    'StageCache', 'UNVERIFIED_BADGES', 'canonical_json', 'check', 'dump_json', 'get', 'load_arrays',
    'load_json', 'load_overrides', 'network_guard', 'register_defaults', 'resolve', 'save_arrays',
    'sha256_bytes', 'sha256_file', 'snapshot', 'taint', 'unverified_count',
]
