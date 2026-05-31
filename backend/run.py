"""Backend launcher with a Windows-safe default for Uvicorn reload."""

from __future__ import annotations

import os
import platform

import uvicorn


reload_enabled = os.getenv("UVICORN_RELOAD", "").strip().lower() in {"1", "true", "yes", "on"}
if not reload_enabled:
    reload_enabled = platform.system() != "Windows"


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=os.getenv("UVICORN_HOST", "127.0.0.1"),
        port=int(os.getenv("UVICORN_PORT", "8000")),
        reload=reload_enabled,
    )


if __name__ == "__main__":
    main()
