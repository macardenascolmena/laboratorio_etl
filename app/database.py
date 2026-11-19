from pymongo import MongoClient                            # cliente de MongoDB
from sqlalchemy import create_engine                       # motor de conexión SQL
from sqlalchemy.orm import declarative_base, sessionmaker  # base de modelos y fábrica de sesiones

from app import config  # nuestras constantes de configuración

# ======================= MONGODB =======================
# MongoClient no abre la conexión de inmediato: se conecta en la primera operación.
mongo_client = MongoClient(config.MONGO_URI)
# Selecciona la base de datos (Mongo la crea al insertar el primer documento).
mongo_db = mongo_client[config.MONGO_DB]
# Colección = "tabla" de Mongo. Aquí vive la data cruda (staging).
coleccion_raw = mongo_db[config.MONGO_COLLECTION]

# ======================== MYSQL ========================
# Engine = administrador de conexiones a MySQL.
# pool_pre_ping=True: verifica que la conexión siga viva antes de usarla.
engine = create_engine(config.MYSQL_URL, pool_pre_ping=True)

# Fábrica de sesiones. autoflush=False y autocommit=False: nada se envía
# a la base hasta que hagamos commit explícito.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Clase padre de todos los modelos. Guarda el catálogo de tablas (Base.metadata).
Base = declarative_base()


def get_db():
    """Entrega una sesión SQL por petición y la cierra al terminar."""
    db = SessionLocal()   # abre la sesión
    try:
        yield db          # FastAPI la inyecta en el controller
    finally:
        db.close()        # siempre se cierra, aunque haya errores