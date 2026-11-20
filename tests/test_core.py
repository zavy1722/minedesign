import json
import socket
from datetime import datetime, timezone

import numpy as np
import pytest

from face3d.core import config
from face3d.core.audit import AuditLog
from face3d.core.cache import StageCache
from face3d.core.config import Default
from face3d.core.policy import (ConsentRecord, DataClass, LicenceTag, Scope, check,
                                network_guard, taint)
from face3d.core.schema import (FormatError, canonical_json, dump_json, load_arrays, load_json,
                                save_arrays, sha256_file)

NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_json_format_version_roundtrip_and_refusals(tmp_path):
    p = tmp_path / "a.json"
    dump_json({"x": np.arange(3), "y": float("nan")}, p, format="f3d.test", version=2)
    d = load_json(p, expect_format="f3d.test", max_version=2)
    assert d["x"] == [0, 1, 2] and d["y"] is None and "NaN" not in p.read_text()
    with pytest.raises(FormatError):
        load_json(p, expect_format="other")
    with pytest.raises(FormatError):
        load_json(p, expect_format="f3d.test", max_version=1)
    arr = np.arange(6.0).reshape(2, 3)
    man = save_arrays(tmp_path / "a.npz", a=arr)
    assert load_arrays(tmp_path / "a.npz", man)["a"].shape == (2, 3)
    man["a"]["sha256"] = "0" * 64
    with pytest.raises(FormatError):
        load_arrays(tmp_path / "a.npz", man)
    assert len(sha256_file(p)) == 64


def test_canonical_json_stable():
    a = canonical_json({"a": np.array([1.0, 2.5]), "b": 1})
    b = canonical_json({"b": 1, "a": [1.0, 2.5]})
    assert a == b


def test_defaults_registry_badges_overrides_bounds(tmp_path):
    with pytest.raises(ValueError):
        Default(1, "x", "src")
    config.register_defaults("t_core", {
        "a": Default(1.0, "\U0001F9E0", "note", "mm", (0.0, 2.0)),
        "b": Default(3, "\u2705", "note"),
    })
    config.register_defaults("t_core", {"b": Default(3, "\u2705", "note")})  # idempotent
    with pytest.raises(ValueError):
        config.register_defaults("t_core", {"b": Default(4, "\u2705", "note")})
    assert config.get("t_core.a").unit == "mm"
    toml = tmp_path / "o.toml"
    toml.write_text("[t_core]\n'a' = 1.5\n")
    r = config.resolve(config.load_overrides(toml))
    assert r["t_core.a"] == 1.5
    with pytest.raises(ValueError, match="t_core.a"):
        config.resolve({"t_core": {"a": 9.0}})
    base = config.unverified_count()
    assert config.unverified_count({"t_core.a": 1, "t_core.b": 3}) == 1
    assert base >= 1
    assert "t_core.a" in config.snapshot()
    json.dumps(config.snapshot())


def _rec(**kw):
    d = dict(consent_id="c", subject_pseudonym="s", signer_role="self", consent_text_version="1",
             method="paper", signed_at="2026-01-01T00:00:00", expires_at=None,
             jurisdiction_tags=[], photo_sha256=["h1"], retention_days=0,
             revocation_contact="x", scopes=Scope(0))
    d.update(kw)
    return ConsentRecord(**d)


def test_consent_gates_table():
    kw = dict(now=NOW)
    table = {
        "reconstruct": (Scope.RECONSTRUCT, dict(photos_sha256=["h1"])),
        "identity_keys": (Scope.RECONSTRUCT, {}),
        "expression_keys": (Scope.RIG_ANIMATE, {}),
        "texture": (Scope.TEXTURE, dict(rights_basis=["self_shot"])),
        "store_raw": (Scope.STORE_RAW, dict(rights_basis=["self_shot"])),
        "identity_check": (Scope.IDENTITY_CHECK, {}),
        "network": (Scope.CLOUD_PROCESSING, dict(network_enabled=True, online_access=True)),
        "publish": (Scope.PUBLISH_NONCOMMERCIAL, {}),
        "commercial_export": (Scope.COMMERCIAL, dict(result_commercial_ok=True)),
        "print": (Scope.PRINT_3D, {}),
        "training": (Scope.AI_TRAINING, {}),
    }
    for op, (scope, extra) in table.items():
        assert check(op, _rec(scopes=scope), **extra, **kw).allowed, op
        res = check(op, _rec(scopes=Scope(0)), **extra, **kw)
        assert not res.allowed and res.missing, op
    assert Scope.RECONSTRUCT.name in check("reconstruct", _rec(), photos_sha256=["h1"], **kw).missing
    assert not check("reconstruct", None, **kw).allowed
    s = Scope.RECONSTRUCT
    assert not check("reconstruct", _rec(scopes=s, expires_at="2026-01-02T00:00:00"),
                     photos_sha256=["h1"], **kw).allowed
    assert not check("reconstruct", _rec(scopes=s), photos_sha256=["zz"], **kw).allowed
    assert not check("reconstruct", _rec(scopes=s, attested_age=15), photos_sha256=["h1"], **kw).allowed
    assert check("reconstruct", _rec(scopes=s, attested_age=15, signer_role="guardian"),
                 photos_sha256=["h1"], **kw).allowed
    c = Scope.COMMERCIAL
    assert not check("commercial_export", _rec(scopes=c, deceased=True),
                     result_commercial_ok=True, **kw).allowed
    assert check("commercial_export", _rec(scopes=c, deceased=True, signer_role="estate"),
                 result_commercial_ok=True, **kw).allowed
    assert not check("commercial_export", _rec(scopes=c), result_commercial_ok=None, **kw).allowed
    assert not check("texture", _rec(scopes=Scope.TEXTURE), rights_basis=["unknown"], **kw).allowed
    r = _rec(scopes=Scope.RECONSTRUCT | Scope.TEXTURE)
    assert ConsentRecord.from_json(r.to_json()) == r


def test_taint_null_fails_closed():
    ok = LicenceTag("MIT", True, True)
    assert taint([ok, ok])
    assert not taint([ok, LicenceTag("?", None, None)])
    assert not taint([ok, LicenceTag("NC", False, True)])


def test_stage_cache_keys_and_ttl(tmp_path):
    k = StageCache.key("s", {"img": "h"}, {"a": 1}, 0, "1")
    assert k != StageCache.key("s", {"img": "h"}, {"a": 2}, 0, "1")
    assert k != StageCache.key("s", {"img": "h"}, {"a": 1}, 1, "1")
    assert k == StageCache.key("s", {"img": "h"}, {"a": 1}, 0, "1")
    c = StageCache(root=tmp_path)
    c.put(k, {"v": np.ones(3)}, DataClass.BIOMETRIC_GEOMETRY)
    assert list(tmp_path.iterdir()) == []
    assert c.get(k)["v"].sum() == 3
    c.put("k2", {"v": np.ones(2), "n": 5}, DataClass.LIKENESS_ASSET)
    assert (tmp_path / "k2.npz").exists()
    c2 = StageCache(root=tmp_path)
    got = c2.get("k2")
    assert got["n"] == 5 and got["v"].shape == (2,)
    purged = c.purge(DataClass.BIOMETRIC_GEOMETRY)
    assert purged == [k]
    assert (tmp_path / "k2.json").exists()
    assert c.purge() == ["k2"] and not (tmp_path / "k2.json").exists()
    c.put("k3", {"n": 1}, DataClass.LIKENESS_ASSET)
    c.close()
    assert c.get("k3") is not None  # 30-day TTL entry survives close, loaded from disk


def test_audit_log_rejects_coordinates_and_paths(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.write("reconstruct", DataClass.BIOMETRIC_GEOMETRY, "a" * 64, scope="RECONSTRUCT",
              detail_code="ok")
    rec = json.loads((tmp_path / "audit.jsonl").read_text().splitlines()[0])
    assert set(rec) == {"event", "time", "data_class", "sha256", "scope", "detail_code"}
    for bad in ("/home/u/face.jpg", "C:\\x\\y.png", np.zeros(3), [1.0, 2.0]):
        with pytest.raises(ValueError):
            log.write("e", DataClass.PERSONAL_IMAGE, "a" * 64, detail_code=bad)
    with pytest.raises(ValueError):
        log.write("e", DataClass.PERSONAL_IMAGE, "/tmp/x")
    assert len((tmp_path / "audit.jsonl").read_text().splitlines()) == 1


def test_network_guard_blocks_socket():
    with network_guard():
        with pytest.raises(PermissionError):
            socket.create_connection(("127.0.0.1", 9))
        s = socket.socket()
        try:
            with pytest.raises(PermissionError):
                s.connect(("127.0.0.1", 9))
        finally:
            s.close()
    assert socket.create_connection is not None


# ---------------------------------------------------------------- review regressions
def test_rights_basis_fails_closed():
    kw = dict(now=NOW)
    for op, sc in (("texture", Scope.TEXTURE), ("store_raw", Scope.STORE_RAW)):
        r = _rec(scopes=sc)
        for bad in ("unknown", ["unknown"], None, [None], [""], ["UNKNOWN"], ["unknwon"],
                    ["own"], (), ["self_shot", "unknown"]):
            assert not check(op, r, rights_basis=bad, **kw).allowed, (op, bad)
        assert check(op, r, rights_basis="self_shot", **kw).allowed
        assert check(op, r, rights_basis=["cc_licence", "public_domain"], **kw).allowed


def test_gate_semantics_regressions():
    kw = dict(now=NOW)
    # network needs both flags even with scope
    r = _rec(scopes=Scope.CLOUD_PROCESSING)
    assert not check("network", r, network_enabled=False, online_access=True, **kw).allowed
    assert not check("network", r, network_enabled=True, online_access=False, **kw).allowed
    # expression_keys needs RIG_ANIMATE, not RECONSTRUCT
    assert not check("expression_keys", _rec(scopes=Scope.RECONSTRUCT), **kw).allowed
    # expiry applies to every operation
    exp = "2026-01-02T00:00:00"
    assert not check("print", _rec(scopes=Scope.PRINT_3D, expires_at=exp), **kw).allowed
    # deceased: publish with COMMERCIAL, training, print, expression_keys need estate
    d = dict(deceased=True)
    assert not check("publish", _rec(scopes=Scope.COMMERCIAL, **d), **kw).allowed
    assert check("publish", _rec(scopes=Scope.PUBLISH_NONCOMMERCIAL, **d), **kw).allowed
    for op, sc in (("training", Scope.AI_TRAINING), ("print", Scope.PRINT_3D),
                   ("expression_keys", Scope.RIG_ANIMATE)):
        assert not check(op, _rec(scopes=sc, **d), **kw).allowed, op
        assert check(op, _rec(scopes=sc, signer_role="estate", **d), **kw).allowed, op
    # minor block still names the missing scope
    res = check("print", _rec(scopes=Scope(0), attested_age=15), **kw)
    assert not res.allowed and res.missing == ["PRINT_3D"]
    # malformed records deny instead of raising
    s = Scope.RECONSTRUCT
    assert not check("reconstruct", _rec(scopes=s, expires_at="garbage"),
                     photos_sha256=["h1"], **kw).allowed
    assert not check("reconstruct", _rec(scopes=s, attested_age="15"),
                     photos_sha256=["h1"], **kw).allowed
    # POLICY is read-only
    from face3d.core.policy import POLICY
    with pytest.raises(TypeError):
        POLICY["min_self_consent_age"] = 10
    assert not taint([])


def test_network_guard_restores_and_blocks_more():
    orig = (socket.socket.connect, socket.socket.connect_ex, socket.socket.sendto,
            socket.create_connection, socket.getaddrinfo)
    with network_guard():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            with pytest.raises(PermissionError):
                s.connect_ex(("127.0.0.1", 9))
            with pytest.raises(PermissionError):
                s.sendto(b"x", ("127.0.0.1", 9))
        finally:
            s.close()
        with pytest.raises(PermissionError):
            socket.getaddrinfo("localhost", 9)
    assert orig == (socket.socket.connect, socket.socket.connect_ex, socket.socket.sendto,
                    socket.create_connection, socket.getaddrinfo)


def test_config_override_validation_regressions(tmp_path):
    config.register_defaults("t_core2", {
        "a": Default(1.0, "✅", "n", "", (0.0, 2.0)),
        "u": Default(1.0, "✅", "n"),
        "i": Default(3, "✅", "n"),
    })
    t = tmp_path / "n.toml"
    t.write_text("[t_core2]\n'a' = nan\n")
    with pytest.raises(ValueError, match="t_core2.a"):
        config.resolve(config.load_overrides(t))
    for key, bad in (("a", "oops"), ("u", "oops"), ("a", True), ("i", 2.5), ("i", True)):
        with pytest.raises(ValueError, match=f"t_core2.{key}"):
            config.resolve({"t_core2": {key: bad}})
    assert config.resolve({"t_core2": {"u": 2}})["t_core2.u"] == 2
    with pytest.raises(ValueError):
        Default(5.0, "✅", "s", "", (0, 1))
    config.register_defaults("t_core2", {"arr": Default(np.zeros(2), "✅", "n")})
    config.register_defaults("t_core2", {"arr": Default(np.zeros(2), "✅", "n")})
    json.dumps(config.snapshot())
    # badge counting: exactly the three unverified badges
    m = {k: Default(1, b, "s") for k, b in zip("abcdef", config.BADGES)}
    config.register_defaults("t_badges", m)
    assert config.unverified_count({f"t_badges.{k}": 1 for k in "abcdef"}) == 3


def test_cache_disk_regressions(tmp_path):
    c = StageCache(root=tmp_path)
    with pytest.raises(TypeError):
        c.put("k", {"albedo": np.ones((2, 2)), "src": object()}, DataClass.LIKENESS_ASSET)
    assert list(tmp_path.iterdir()) == []
    c.put("k", {"v": np.ones(3), "n": float("nan")}, DataClass.LIKENESS_ASSET)
    c.put("k", {"n": 1}, DataClass.LIKENESS_ASSET)
    assert StageCache(root=tmp_path).get("k") == {"n": 1}
    c.put("nan", {"n": float("nan")}, DataClass.LIKENESS_ASSET)
    assert np.isnan(StageCache(root=tmp_path).get("nan")["n"])
    (tmp_path / "list.json").write_text("[1,2]")
    (tmp_path / "orph.npz").write_bytes(b"x")
    assert set(c.purge()) >= {"k", "nan", "list", "orph"}
    assert list(tmp_path.iterdir()) == []
    # get returns a copy
    c.put("m", {"a": 1}, DataClass.LIKENESS_ASSET)
    c.get("m")["a"] = 2
    assert c.get("m")["a"] == 1
    # close purges TTL-0 entries written under a larger ttl
    big = StageCache(root=tmp_path, ttl_days={DataClass.BIOMETRIC_GEOMETRY: 5})
    big.put("g", {"n": 1}, DataClass.BIOMETRIC_GEOMETRY)
    assert (tmp_path / "g.json").exists()
    StageCache(root=tmp_path).close()
    assert not (tmp_path / "g.json").exists()
    # policy bounds on ttl
    with pytest.raises(ValueError):
        StageCache(root=tmp_path, ttl_days={DataClass.BIOMETRIC_TEMPLATE: 5})
    with pytest.raises(ValueError):
        StageCache(root=tmp_path, ttl_days={DataClass.BIOMETRIC_GEOMETRY: 400})


def test_audit_log_stricter(tmp_path):
    log = AuditLog(tmp_path / "a.jsonl")
    for bad in ("~/x", "C:x", "1510.2,2011.7,1622.0,2040.1", "[[1510.2,2011.7]]", "IMG_0412.HEIC",
                "John Smith"):
        with pytest.raises(ValueError):
            log.write("e", DataClass.PERSONAL_IMAGE, "a" * 64, detail_code=bad)
    with pytest.raises(ValueError):
        log.write("e", DataClass.PERSONAL_IMAGE, "John Smith")
    log.write("e", DataClass.PERSONAL_IMAGE, "")


def test_schema_edge_cases(tmp_path):
    assert canonical_json({"x": float("nan")}) != canonical_json({"x": None})
    assert canonical_json({"x": float("nan")}) != canonical_json({"x": float("inf")})
    with pytest.raises(ValueError):
        canonical_json({1: "a", "1": "b"})
    arr = np.zeros((2, 3))
    man = save_arrays(tmp_path / "a.npz", a=arr)
    bad = {"a": dict(man["a"], shape=[3, 2])}
    with pytest.raises(FormatError):
        load_arrays(tmp_path / "a.npz", bad)
    bad = {"a": dict(man["a"], dtype="int64")}
    with pytest.raises(FormatError):
        load_arrays(tmp_path / "a.npz", bad)
    p = tmp_path / "n.json"
    p.write_text('{"format":"f","version":1,"x":NaN}')
    with pytest.raises(FormatError):
        load_json(p)
    p.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(FormatError):
        load_json(p)
