"""Equirectangular pano pixel -> cubemap face index and face pixel coords."""

from __future__ import annotations

import math


def equirect_pixel_to_direction(x: float, y: float, width: int, height: int) -> tuple[float, float, float]:
    """Top-left image origin; longitude/latitude on unit sphere (Y up)."""
    u = x / float(width)
    v = y / float(height)
    lon = (u - 0.5) * 2.0 * math.pi
    lat = (0.5 - v) * math.pi
    clat = math.cos(lat)
    return clat * math.sin(lon), math.sin(lat), clat * math.cos(lon)


def direction_to_cubemap_face(x: float, y: float, z: float) -> tuple[int, float, float]:
    """
    Face order: 0=+X, 1=-X, 2=+Y, 3=-Y, 4=+Z, 5=-Z.
    Returns (face, u, v) with u,v in [-1, 1].
    """
    ax, ay, az = abs(x), abs(y), abs(z)
    if az >= ax and az >= ay:
        if z >= 0:
            return 4, x / az, -y / az
        return 5, -x / az, -y / az
    if ax >= ay:
        if x >= 0:
            return 0, -z / ax, -y / ax
        return 1, z / ax, -y / ax
    if y >= 0:
        return 2, x / ay, z / ay
    return 3, x / ay, -z / ay


def cubemap_uv_to_pixel(u: float, v: float, face_size: int) -> tuple[float, float]:
    if face_size <= 1:
        return 0.0, 0.0
    s = face_size - 1
    px = (u + 1.0) * 0.5 * s
    py = (1.0 - v) * 0.5 * s  # image Y down
    return px, py


def equirect_to_cubemap_pixel(
    x: float,
    y: float,
    *,
    pano_width: int,
    pano_height: int,
    face_size: int,
) -> tuple[int, float, float]:
    dx, dy, dz = equirect_pixel_to_direction(x, y, pano_width, pano_height)
    face, u, v = direction_to_cubemap_face(dx, dy, dz)
    px, py = cubemap_uv_to_pixel(u, v, face_size)
    return face, px, py
