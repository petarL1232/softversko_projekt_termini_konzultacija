#from collections.abc import Generator Takoder ostalo od kostura, mislim da je to antunov dio..?
import os

from dotenv import load_dotenv

from sqlmodel import (
    Session,
    create_engine
)

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL)


def get_session():

    return Session(engine)

#def get_session() -> Generator[Session, None, None]:
#    """FastAPI dependency that provides a database session."""
#
#   with Session(engine) as session:
#        yield session
# Ostalo od kostura, po potrebi zamijeniti postojeći get_session() Opet, ako je ovo antun dio 
# ali vrlo je moguce da sam ja lud, ovo ovako funkcionira no valjda moze biti bolje..? - Ivano 
