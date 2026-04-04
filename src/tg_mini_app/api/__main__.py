from __future__ import annotations

import uvicorn

from tg_mini_app.api.app import create_app
from tg_mini_app.settings import get_settings


def main() -> None:
    app = create_app()
    settings = get_settings()
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()

