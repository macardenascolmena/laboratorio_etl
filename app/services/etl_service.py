import pandas as pd                                            # transformación tabular
import requests                                                # llamadas HTTP a la API pública
from pymongo import ReplaceOne                                 # upsert en bloque para Mongo
from sqlalchemy import func, select, text                      # construcción de SQL
from sqlalchemy.dialects.mysql import insert as mysql_insert   # INSERT ... ON DUPLICATE KEY UPDATE

from app import config
from app.database import Base, coleccion_raw, engine
from app.models.entidad_sql import PersonajeMaster


class SinDatosError(Exception):
    """Mongo está vacío y no hay nada que transformar."""


# ===================== ENDPOINT A: EXTRACT =====================
def _descargar_personajes(cantidad: int) -> list[dict]:
    """Recorre las páginas de la API hasta juntar 'cantidad' personajes."""
    personajes: list[dict] = []
    url = config.API_URL                      # primera página

    while url and len(personajes) < cantidad:
        respuesta = requests.get(url, timeout=15)   # timeout: no se cuelga la demo
        respuesta.raise_for_status()                # error 4xx/5xx -> excepción
        datos = respuesta.json()
        personajes.extend(datos["results"])         # 20 personajes por página
        url = datos["info"]["next"]                 # None en la última página

    return personajes[:cantidad]                    # recorta al número exacto


def extraer(cantidad: int) -> dict:
    """Descarga personajes y los guarda en Mongo de forma idempotente."""
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor que 0")

    personajes = _descargar_personajes(cantidad)
    ids = [p["id"] for p in personajes]

    # Cuáles de estos ids ya están en Mongo (proyección: solo traemos el _id).
    existentes = {d["_id"] for d in coleccion_raw.find({"_id": {"$in": ids}}, {"_id": 1})}

    operaciones = []
    for p in personajes:
        doc = dict(p)
        doc["_id"] = doc.pop("id")   # PK natural: el id de la API pasa a ser el _id
        # upsert=True: si existe lo reemplaza, si no lo inserta. Nunca duplica.
        operaciones.append(ReplaceOne({"_id": doc["_id"]}, doc, upsert=True))

    if operaciones:                  # bulk_write falla con lista vacía
        coleccion_raw.bulk_write(operaciones)

    ya_existentes = len(existentes)
    return {
        "mensaje": "Datos extraídos exitosamente",
        "nuevos": len(ids) - ya_existentes,
        "ya_existentes": ya_existentes,
        "fuente": config.API_NOMBRE,
    }


# ============== ENDPOINT B: TRANSFORM + LOAD ==============
_COLS_CATEGORICAS = [
    "nombre", "status", "species", "subtipo", "genero",
    "origen_nombre", "ubicacion_nombre",
]


def _transformar(docs: list[dict]) -> pd.DataFrame:
    """Convierte los documentos anidados de Mongo en un DataFrame plano y limpio."""
    # 1) Aplanamiento: {"origin": {"name": "X"}} -> columna "origin.name".
    df = pd.json_normalize(docs)

    # 2) Deja solo las columnas útiles (descarta image, url, etc.). Si alguna
    #    no vino en la API, la crea con NaN en vez de dar KeyError.
    df = df.reindex(columns=[
        "_id", "name", "status", "species", "type", "gender",
        "origin.name", "location.name", "episode", "created",
    ])

    # 3) Nombres claros, iguales a los del modelo SQL.
    df = df.rename(columns={
        "_id": "id_personaje",
        "name": "nombre",
        "type": "subtipo",
        "gender": "genero",
        "origin.name": "origen_nombre",
        "location.name": "ubicacion_nombre",
    })

    # 4) Columnas derivadas.
    df["total_episodios"] = df["episode"].apply(lambda e: len(e) if isinstance(e, list) else None)
    df["esta_vivo"] = df["status"].map(lambda s: None if pd.isna(s) else s == "Alive")
    df["fecha_creacion"] = pd.to_datetime(df["created"], errors="coerce", utc=True).dt.date
    df = df.drop(columns=["episode", "created"])

    # 5) Nulos en texto categórico -> "N/A" (la cadena vacía también cuenta como nulo).
    for col in _COLS_CATEGORICAS:
        df[col] = (
            df[col].astype("string")
            .str.strip()
            .replace("", pd.NA)
            .fillna("N/A")
            .astype(str)
        )
    # Numéricos, fecha y booleano NO se rellenan: quedan NULL.

    # 6) Un mismo id no puede repetirse dentro del lote.
    return df.drop_duplicates(subset="id_personaje")


def transformar_y_cargar(db) -> dict:
    """Lee Mongo, limpia con Pandas y hace UPSERT en MySQL."""
    # Resiliencia: crea la tabla si no existe, conservando la PK del modelo.
    Base.metadata.create_all(bind=engine)

    docs = list(coleccion_raw.find({}))
    if not docs:
        raise SinDatosError("MongoDB está vacío. Ejecute primero POST /api/v1/etl/extraer")

    df = _transformar(docs)

    # NaN/NaT/NA -> None, para que MySQL reciba NULL real.
    df = df.astype(object).where(df.notna(), None)
    registros = df.to_dict(orient="records")

    columnas_no_pk = [c.name for c in PersonajeMaster.__table__.columns if not c.primary_key]
    for i in range(0, len(registros), 500):          # bloques de 500 filas
        bloque = registros[i:i + 500]
        stmt = mysql_insert(PersonajeMaster).values(bloque)
        # Si la PK ya existe, actualiza en vez de duplicar.
        stmt = stmt.on_duplicate_key_update(
            **{c: stmt.inserted[c] for c in columnas_no_pk}
        )
        db.execute(stmt)
    db.commit()

    return {
        "mensaje": "Pipeline finalizado",
        "registros_procesados": len(registros),
        "tabla_destino": PersonajeMaster.__tablename__,
    }


# ===================== ENDPOINT C: RESET =====================
def reset() -> dict:
    """Vacía Mongo y hace TRUNCATE en MySQL. La tabla SQL se conserva."""
    mongo_borrados = coleccion_raw.delete_many({}).deleted_count

    Base.metadata.create_all(bind=engine)   # por si la tabla no existía

    with engine.begin() as conn:
        # Contamos antes de truncar para poder informar cuántas filas había.
        filas = conn.execute(select(func.count()).select_from(PersonajeMaster)).scalar()
        # TRUNCATE vacía la tabla pero conserva su estructura (DROP la borraría).
        conn.execute(text(f"TRUNCATE TABLE {PersonajeMaster.__tablename__}"))

    return {
        "mensaje": "Sistema reseteado correctamente",
        "mongo_docs_eliminados": mongo_borrados,
        "mysql_rows_eliminadas": int(filas or 0),
    }