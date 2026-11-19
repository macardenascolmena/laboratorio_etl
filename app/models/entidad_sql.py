from sqlalchemy import Boolean, Column, Date, Integer, String

from app.database import Base  # clase padre común


class PersonajeMaster(Base):
    # Nombre físico de la tabla en MySQL.
    __tablename__ = "personajes_master"

    # PK = _id de Mongo = id de la API. autoincrement=False es CRÍTICO:
    # si MySQL inventara ids, se rompería la PK alineada y el perfil dual.
    id_personaje = Column(Integer, primary_key=True, autoincrement=False)

    # Texto categórico: no admite NULL porque los vacíos se rellenan con "N/A".
    nombre = Column(String(150), nullable=False)
    status = Column(String(30), nullable=False)
    species = Column(String(60), nullable=False)
    subtipo = Column(String(100), nullable=False)           # viene de "type"
    genero = Column(String(30), nullable=False)             # viene de "gender"
    origen_nombre = Column(String(150), nullable=False)     # aplanada de origin.name
    ubicacion_nombre = Column(String(150), nullable=False)  # aplanada de location.name

    # Numérico, booleano y fecha: SÍ admiten NULL (no se rellenan con 0).
    total_episodios = Column(Integer, nullable=True)        # derivada: len(episode)
    esta_vivo = Column(Boolean, nullable=True)              # derivada: status == "Alive"
    fecha_creacion = Column(Date, nullable=True)            # derivada: created -> DATE