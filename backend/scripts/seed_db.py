from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.database import AsyncSessionLocal, init_db
from app.models import Place
from app.services.geohash import encode

SEED_PLACES = [
    {"name": "AIIMS Delhi", "place_type": "hospital", "latitude": 28.5672, "longitude": 77.2100, "phone": "011-26588500", "address": "Ansari Nagar, New Delhi", "is_verified": True},
    {"name": "Apollo Hospital Delhi", "place_type": "hospital", "latitude": 28.5494, "longitude": 77.2001, "phone": "011-26925858", "address": "Mathura Road, New Delhi", "is_verified": True},
    {"name": "Delhi Police HQ", "place_type": "police", "latitude": 28.6360, "longitude": 77.2261, "phone": "011-23490000", "address": "ITO, New Delhi", "is_verified": True},
    {"name": "CATS Ambulance Delhi", "place_type": "ambulance", "latitude": 28.6139, "longitude": 77.2090, "phone": "102", "address": "Centralized Ambulance Trauma Services", "is_verified": True},
    {"name": "KEM Hospital Mumbai", "place_type": "hospital", "latitude": 18.9940, "longitude": 72.8404, "phone": "022-24107000", "address": "Parel, Mumbai", "is_verified": True},
    {"name": "Hinduja Hospital Mumbai", "place_type": "hospital", "latitude": 19.0595, "longitude": 72.8316, "phone": "022-24452222", "address": "Mahim, Mumbai", "is_verified": True},
    {"name": "Mumbai Police Control Room", "place_type": "police", "latitude": 18.9388, "longitude": 72.8354, "phone": "100", "address": "Crawford Market, Mumbai", "is_verified": True},
    {"name": "Mumbai Fire Brigade HQ", "place_type": "fire_station", "latitude": 18.9515, "longitude": 72.8322, "phone": "101", "address": "Byculla, Mumbai", "is_verified": True},
    {"name": "National Highway Towing - NH8", "place_type": "towing", "latitude": 28.4745, "longitude": 77.0266, "phone": "1800-180-1234", "address": "NH8, Gurgaon", "is_verified": True},
    {"name": "BPCL Petrol Pump Andheri", "place_type": "fuel", "latitude": 19.1197, "longitude": 72.8467, "phone": "022-26204567", "address": "Andheri West, Mumbai", "is_verified": True},
]


async def main() -> None:
    await init_db()
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        upserted = 0
        for row in SEED_PLACES:
            result = await session.execute(select(Place).where(Place.name == row["name"]))
            existing = result.scalar_one_or_none()
            if existing is None:
                session.add(
                    Place(
                        name=row["name"],
                        place_type=row["place_type"],
                        latitude=row["latitude"],
                        longitude=row["longitude"],
                        phone=row["phone"],
                        address=row["address"],
                        is_verified=row["is_verified"],
                        geohash5=encode(row["latitude"], row["longitude"], precision=5),
                        source="manual_verified",
                        last_synced=now,
                        created_at=now,
                    )
                )
            else:
                existing.place_type = row["place_type"]
                existing.latitude = row["latitude"]
                existing.longitude = row["longitude"]
                existing.phone = row["phone"]
                existing.address = row["address"]
                existing.is_verified = row["is_verified"]
                existing.geohash5 = encode(row["latitude"], row["longitude"], precision=5)
                existing.source = "manual_verified"
                existing.last_synced = now
            upserted += 1

        await session.commit()

    print(f"Seeded {upserted} emergency places.")


if __name__ == "__main__":
    asyncio.run(main())
