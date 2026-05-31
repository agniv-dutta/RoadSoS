from __future__ import annotations

import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import AsyncSessionLocal, init_db
from app.services.demo_seed import seed_mumbai_places


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as session:
        count = await seed_mumbai_places(session)
    print(f'Seeded {count} verified Mumbai emergency places.')


if __name__ == '__main__':
    asyncio.run(main())
