from __future__ import annotations

from app.bootstrap.container import get_container


def main() -> None:
    get_container().worker.app_worker.run_forever()


if __name__ == "__main__":
    main()
