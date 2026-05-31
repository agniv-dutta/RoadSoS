from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Place
from app.services.geohash import encode


DEMO_PLACES = [
    {
        'name': 'KEM Hospital Emergency Wing',
        'place_type': 'hospital',
        'latitude': 19.0008,
        'longitude': 72.8411,
        'phone': '02224136051',
        'address': 'Acharya Donde Marg, Parel, Mumbai',
    },
    {
        'name': 'Sion Hospital Casualty',
        'place_type': 'hospital',
        'latitude': 19.0469,
        'longitude': 72.8634,
        'phone': '02224076381',
        'address': 'Dr Babasaheb Ambedkar Rd, Sion, Mumbai',
    },
    {
        'name': 'Dadar Police Station',
        'place_type': 'police',
        'latitude': 19.0207,
        'longitude': 72.8434,
        'phone': '02224146544',
        'address': 'Senapati Bapat Marg, Dadar West, Mumbai',
    },
    {
        'name': '108 Ambulance Dispatch - Central Zone',
        'place_type': 'ambulance',
        'latitude': 19.0312,
        'longitude': 72.8592,
        'phone': '108',
        'address': 'Central Dispatch Hub, Mumbai',
    },
    {
        'name': 'Mumbai Express Recovery Towing',
        'place_type': 'towing',
        'latitude': 19.0474,
        'longitude': 72.8576,
        'phone': '02224937777',
        'address': 'Prabhadevi Service Lane, Mumbai',
    },
]


MUMBAI_SEED_PLACES = [
    {
        'name': 'KEM Hospital Emergency Wing',
        'place_type': 'hospital',
        'latitude': 19.0008,
        'longitude': 72.8411,
        'phone': '02224136051',
        'address': 'Acharya Donde Marg, Parel, Mumbai',
    },
    {
        'name': 'Sion Hospital Casualty',
        'place_type': 'hospital',
        'latitude': 19.0469,
        'longitude': 72.8634,
        'phone': '02224076381',
        'address': 'Dr Babasaheb Ambedkar Rd, Sion, Mumbai',
    },
    {
        'name': 'Nair Hospital Emergency',
        'place_type': 'hospital',
        'latitude': 18.9684,
        'longitude': 72.8195,
        'phone': '02223027000',
        'address': 'Dr A L Nair Rd, Mumbai Central, Mumbai',
    },
    {
        'name': 'JJ Hospital Trauma Center',
        'place_type': 'hospital',
        'latitude': 18.9627,
        'longitude': 72.8331,
        'phone': '02223735555',
        'address': 'Byculla, Mumbai',
    },
    {
        'name': 'Cooper Hospital Emergency',
        'place_type': 'hospital',
        'latitude': 19.1075,
        'longitude': 72.8376,
        'phone': '02226207254',
        'address': 'Juhu, Mumbai',
    },
    {
        'name': 'Rajawadi Hospital Emergency',
        'place_type': 'hospital',
        'latitude': 19.0798,
        'longitude': 72.9075,
        'phone': '02221027341',
        'address': 'Ghatkopar East, Mumbai',
    },
    {
        'name': 'Bhabha Hospital Emergency',
        'place_type': 'hospital',
        'latitude': 19.0618,
        'longitude': 72.8348,
        'phone': '02226422775',
        'address': 'Bandra West, Mumbai',
    },
    {
        'name': 'SevenHills Hospital Emergency',
        'place_type': 'hospital',
        'latitude': 19.1212,
        'longitude': 72.8784,
        'phone': '02267676767',
        'address': 'Andheri East, Mumbai',
    },
    {
        'name': 'Hinduja Hospital Emergency',
        'place_type': 'hospital',
        'latitude': 19.0359,
        'longitude': 72.8416,
        'phone': '02224452222',
        'address': 'Mahim West, Mumbai',
    },
    {
        'name': 'Lilavati Hospital Emergency',
        'place_type': 'hospital',
        'latitude': 19.0515,
        'longitude': 72.8268,
        'phone': '02226751000',
        'address': 'Bandra West, Mumbai',
    },
    {
        'name': 'Dadar Police Station',
        'place_type': 'police',
        'latitude': 19.0207,
        'longitude': 72.8434,
        'phone': '02224146544',
        'address': 'Senapati Bapat Marg, Dadar West, Mumbai',
    },
    {
        'name': 'Bandra Police Station',
        'place_type': 'police',
        'latitude': 19.0546,
        'longitude': 72.8301,
        'phone': '02226423151',
        'address': 'Hill Road, Bandra West, Mumbai',
    },
    {
        'name': 'Andheri Police Station',
        'place_type': 'police',
        'latitude': 19.1197,
        'longitude': 72.8468,
        'phone': '02226830160',
        'address': 'Andheri West, Mumbai',
    },
    {
        'name': 'Kurla Police Station',
        'place_type': 'police',
        'latitude': 19.0734,
        'longitude': 72.8796,
        'phone': '02226502459',
        'address': 'Kurla West, Mumbai',
    },
    {
        'name': 'Mumbai Traffic Control Room',
        'place_type': 'police',
        'latitude': 18.9446,
        'longitude': 72.8356,
        'phone': '02224937755',
        'address': 'Worli Traffic HQ, Mumbai',
    },
    {
        'name': '108 Ambulance Dispatch - South Mumbai',
        'place_type': 'ambulance',
        'latitude': 18.9672,
        'longitude': 72.8243,
        'phone': '108',
        'address': 'South Mumbai EMS Coordination Desk',
    },
    {
        'name': '108 Ambulance Dispatch - Central Zone',
        'place_type': 'ambulance',
        'latitude': 19.0312,
        'longitude': 72.8592,
        'phone': '108',
        'address': 'Central Dispatch Hub, Mumbai',
    },
    {
        'name': '108 Ambulance Dispatch - Western Suburbs',
        'place_type': 'ambulance',
        'latitude': 19.1428,
        'longitude': 72.8421,
        'phone': '108',
        'address': 'Borivali EMS Node, Mumbai',
    },
    {
        'name': 'Mumbai Express Recovery Towing',
        'place_type': 'towing',
        'latitude': 19.0474,
        'longitude': 72.8576,
        'phone': '02224937777',
        'address': 'Prabhadevi Service Lane, Mumbai',
    },
    {
        'name': 'City Crane Towing Services',
        'place_type': 'towing',
        'latitude': 19.0984,
        'longitude': 72.8864,
        'phone': '02228776655',
        'address': 'Powai Link Road, Mumbai',
    },
]


async def seed_places(
    db: AsyncSession,
    *,
    rows: list[dict],
    verified: bool,
    source: str,
    reset_source: bool = False,
) -> int:
    now = datetime.now(timezone.utc)

    if reset_source:
        await db.execute(delete(Place).where(Place.source == source))

    upserted = 0
    for row in rows:
        result = await db.execute(select(Place).where(Place.name == row['name']))
        existing = result.scalar_one_or_none()
        if existing is None:
            existing = Place(
                name=row['name'],
                place_type=row['place_type'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                phone=row['phone'],
                address=row['address'],
                is_verified=verified,
                geohash5=encode(row['latitude'], row['longitude'], precision=5),
                source=source,
                last_synced=now,
                created_at=now,
            )
            db.add(existing)
        else:
            existing.place_type = row['place_type']
            existing.latitude = row['latitude']
            existing.longitude = row['longitude']
            existing.phone = row['phone']
            existing.address = row['address']
            existing.is_verified = verified
            existing.geohash5 = encode(row['latitude'], row['longitude'], precision=5)
            existing.source = source
            existing.last_synced = now
        upserted += 1

    await db.commit()
    return upserted


async def seed_demo_places(db: AsyncSession) -> int:
    return await seed_places(db, rows=DEMO_PLACES, verified=True, source='demo_seed', reset_source=True)


async def seed_mumbai_places(db: AsyncSession) -> int:
    return await seed_places(db, rows=MUMBAI_SEED_PLACES, verified=True, source='manual_verified', reset_source=False)
