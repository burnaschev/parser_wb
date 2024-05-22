from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DB_URL


engine = create_engine(
    url=DB_URL,
    echo=True,
)

session_sync = sessionmaker(bind=engine)





