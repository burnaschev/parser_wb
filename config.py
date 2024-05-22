import os
from sqlalchemy.engine import URL
from dotenv import load_dotenv

load_dotenv()
# db
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DRIVER_NAME = os.getenv('DRIVER_NAME')
DB_URL = URL.create(
        drivername=DRIVER_NAME,
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )

# tg_bot



