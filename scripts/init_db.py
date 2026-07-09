"""Create all tables (dev convenience). For production use Alembic migrations."""
from app.database import Base, engine
import app.models  # noqa: F401 — registers all models


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("All tables created.")


if __name__ == "__main__":
    main()
