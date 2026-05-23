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

    with Session(engine) as session:
        yield session


def create_db_and_tables(): # Dodano u slucaju da je nekome potrebno zbog nekog razloga, zasad bez funkcionalnosti 

    pass        
