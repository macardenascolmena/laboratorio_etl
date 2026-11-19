import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

# ---------------- MongoDB (Staging) ----------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "laboratorio_etl")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "personajes_raw")

# ---------------- MySQL (Data Warehouse) ----------------
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "laboratorio_etl")

# URL de conexión de SQLAlchemy: dialecto+driver://usuario:password@host:puerto/base
# "mysql+mysqlconnector" = MySQL usando el driver mysql-connector-python.
MYSQL_URL = (
    f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)        

# ---------------- API pública (Source) ----------------
API_URL = os.getenv("API_URL", "https://rickandmortyapi.com/api/character")
API_NOMBRE = os.getenv("API_NOMBRE", "Rick & Morty API")
    