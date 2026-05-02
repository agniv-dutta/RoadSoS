from __future__ import annotations

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
BITS = (16, 8, 4, 2, 1)


def encode(latitude: float, longitude: float, precision: int = 5) -> str:
    """Encode coordinates into a geohash string."""

    latitude_interval = [-90.0, 90.0]
    longitude_interval = [-180.0, 180.0]
    geohash: list[str] = []
    bit = 0
    character = 0
    even = True

    while len(geohash) < precision:
        if even:
            midpoint = sum(longitude_interval) / 2
            if longitude >= midpoint:
                character |= BITS[bit]
                longitude_interval[0] = midpoint
            else:
                longitude_interval[1] = midpoint
        else:
            midpoint = sum(latitude_interval) / 2
            if latitude >= midpoint:
                character |= BITS[bit]
                latitude_interval[0] = midpoint
            else:
                latitude_interval[1] = midpoint

        even = not even
        if bit < 4:
            bit += 1
        else:
            geohash.append(BASE32[character])
            bit = 0
            character = 0

    return "".join(geohash)


def decode(geohash: str) -> tuple[float, float]:
    """Decode a geohash string into the center point of its cell."""

    latitude_interval = [-90.0, 90.0]
    longitude_interval = [-180.0, 180.0]
    even = True

    for character in geohash.lower():
        if character not in BASE32:
            raise ValueError(f"Invalid geohash character: {character}")
        character_bits = BASE32.index(character)
        for mask in BITS:
            if even:
                midpoint = sum(longitude_interval) / 2
                if character_bits & mask:
                    longitude_interval[0] = midpoint
                else:
                    longitude_interval[1] = midpoint
            else:
                midpoint = sum(latitude_interval) / 2
                if character_bits & mask:
                    latitude_interval[0] = midpoint
                else:
                    latitude_interval[1] = midpoint
            even = not even

    return (sum(latitude_interval) / 2, sum(longitude_interval) / 2)
