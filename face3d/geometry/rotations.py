"""Rotation helpers (axis-angle / Rodrigues), numpy only."""
from __future__ import annotations

import numpy as np


def skew(v: np.ndarray) -> np.ndarray:
    """3x3 cross-product matrix of a 3-vector."""
    x, y, z = v
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


def rodrigues(rvec: np.ndarray) -> np.ndarray:
    """Axis-angle vector (radians * unit axis) -> 3x3 rotation matrix."""
    rvec = np.asarray(rvec, dtype=float).reshape(3)
    theta = float(np.linalg.norm(rvec))
    if theta < 1e-12:
        # First-order expansion keeps the map smooth around zero.
        return np.eye(3) + skew(rvec)
    k = rvec / theta
    K = skew(k)
    return np.eye(3) + np.sin(theta) * K + (1.0 - np.cos(theta)) * (K @ K)


def rotation_to_rvec(R: np.ndarray) -> np.ndarray:
    """3x3 rotation matrix -> axis-angle vector (inverse of :func:`rodrigues`)."""
    R = np.asarray(R, dtype=float)
    cos_t = np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0)
    theta = float(np.arccos(cos_t))
    if theta < 1e-8:
        return np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / 2.0
    if np.pi - theta < 1e-5:
        # Near 180 degrees: axis from the symmetric part.
        A = (R + np.eye(3)) / 2.0
        i = int(np.argmax(np.diag(A)))
        axis = A[:, i] / np.sqrt(max(A[i, i], 1e-15))
        axis /= np.linalg.norm(axis)
        return axis * theta
    w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return w * (theta / (2.0 * np.sin(theta)))


def nearest_rotation(M: np.ndarray) -> np.ndarray:
    """Closest proper rotation (det=+1) to a 3x3 matrix in Frobenius norm."""
    U, _, Vt = np.linalg.svd(M)
    D = np.eye(3)
    D[2, 2] = np.sign(np.linalg.det(U @ Vt)) or 1.0
    return U @ D @ Vt


def euler_xyz_deg(R: np.ndarray) -> np.ndarray:
    """Rotation matrix -> (pitch, yaw, roll) in degrees, R = Rz @ Ry @ Rx convention."""
    R = np.asarray(R, dtype=float)
    yaw = np.arcsin(-np.clip(R[2, 0], -1.0, 1.0))
    pitch = np.arctan2(R[2, 1], R[2, 2])
    roll = np.arctan2(R[1, 0], R[0, 0])
    return np.degrees([pitch, yaw, roll])


def rotation_from_euler_deg(pitch: float, yaw: float, roll: float) -> np.ndarray:
    """(pitch about x, yaw about y, roll about z) degrees -> R = Rz @ Ry @ Rx."""
    p, y, r = np.radians([pitch, yaw, roll])
    Rx = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    Ry = np.array([[np.cos(y), 0, np.sin(y)], [0, 1, 0], [-np.sin(y), 0, np.cos(y)]])
    Rz = np.array([[np.cos(r), -np.sin(r), 0], [np.sin(r), np.cos(r), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx
