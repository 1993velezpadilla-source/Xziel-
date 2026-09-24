#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass


WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)


@dataclass(frozen=True)
class Geodetic:
    latitude_deg: float
    longitude_deg: float
    height_m: float = 0.0

    def validate(self) -> None:
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("latitude must be within [-90, 90]")
        if not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("longitude must be within [-180, 180]")


@dataclass(frozen=True)
class ECEF:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class ENU:
    east: float
    north: float
    up: float


@dataclass(frozen=True)
class XzielLocal:
    """
    Default HAYUYA -> Xziel local metric convention.

    X = east
    Y = up
    Z = north

    The mapping stays explicit so a future Xziel compiler can swap handedness
    at one boundary instead of contaminating reconstruction/geospatial math.
    """
    x: float
    y: float
    z: float


def geodetic_to_ecef(point: Geodetic) -> ECEF:
    point.validate()
    lat = math.radians(point.latitude_deg)
    lon = math.radians(point.longitude_deg)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)

    prime_vertical = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
    x = (prime_vertical + point.height_m) * cos_lat * cos_lon
    y = (prime_vertical + point.height_m) * cos_lat * sin_lon
    z = (prime_vertical * (1.0 - WGS84_E2) + point.height_m) * sin_lat
    return ECEF(x=x, y=y, z=z)


def ecef_to_enu(point: ECEF, origin: Geodetic) -> ENU:
    origin.validate()
    origin_ecef = geodetic_to_ecef(origin)
    dx = point.x - origin_ecef.x
    dy = point.y - origin_ecef.y
    dz = point.z - origin_ecef.z

    lat = math.radians(origin.latitude_deg)
    lon = math.radians(origin.longitude_deg)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)

    east = -sin_lon * dx + cos_lon * dy
    north = (
        -sin_lat * cos_lon * dx
        - sin_lat * sin_lon * dy
        + cos_lat * dz
    )
    up = (
        cos_lat * cos_lon * dx
        + cos_lat * sin_lon * dy
        + sin_lat * dz
    )
    return ENU(east=east, north=north, up=up)


def geodetic_to_enu(point: Geodetic, origin: Geodetic) -> ENU:
    return ecef_to_enu(geodetic_to_ecef(point), origin)


def enu_to_xziel(point: ENU) -> XzielLocal:
    return XzielLocal(x=point.east, y=point.up, z=point.north)


def geodetic_to_xziel(point: Geodetic, origin: Geodetic) -> XzielLocal:
    return enu_to_xziel(geodetic_to_enu(point, origin))
