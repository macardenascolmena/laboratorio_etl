import pandas as pd
from sqlalchemy import select
from sqlalchemy.types import Boolean, Date, DateTime, Float, Integer, Numeric

from app.database import coleccion_raw, engine
from app.models.entidad_sql import PersonajeMaster

# Objeto Table: contiene las columnas y sus tipos. Es la fuente de la detección dinámica.
TABLA = PersonajeMaster.__table__


class TablaVaciaError(Exception):
    """La tabla SQL no tiene filas todavía."""


def columnas_validas() -> list[str]:
    """Nombres de columnas leídos del modelo (no escritos a mano)."""
    return [c.name for c in TABLA.columns]


def _py(valor):
    """numpy/pandas -> tipos nativos de Python; NaN -> None."""
    if valor is None or pd.isna(valor):
        return None
    if hasattr(valor, "item"):     # numpy.int64, numpy.float64...
        return valor.item()
    return valor


def _detectar_tipo(columna, serie: pd.Series) -> str:
    """Detección dinámica del tipo de análisis a partir del tipo SQL del modelo."""
    tipo_sql = columna.type

    if isinstance(tipo_sql, Boolean):
        return "booleana"
    if isinstance(tipo_sql, (Date, DateTime)):
        return "fecha"
    if isinstance(tipo_sql, (Integer, Float, Numeric)):
        # MySQL guarda BOOLEAN como TINYINT(1): numérica con solo 0 y 1 = booleana.
        valores = set(serie.dropna().unique().tolist())
        if valores and valores <= {0, 1}:
            return "booleana"
        return "numerica"

    # Texto: todos distintos = texto libre; con repetidos = categórica.
    validos = serie.dropna()
    if len(validos) > 0 and validos.nunique() == len(validos):
        return "texto"
    return "categorica"


def analizar_columna(nombre: str) -> dict:
    """Devuelve el análisis estadístico apropiado según el tipo detectado."""
    columna = TABLA.columns[nombre]

    with engine.connect() as conn:
        df = pd.read_sql(select(columna), conn)   # lee solo esa columna
    if df.empty:
        raise TablaVaciaError("La tabla está vacía. Ejecute POST /api/v1/etl/transformar")

    serie = df[nombre]
    nulos = int(serie.isna().sum())
    tipo = _detectar_tipo(columna, serie)
    validos = serie.dropna()

    if tipo == "booleana":
        v = validos.astype(int)
        return {"columna": nombre, "tipo": tipo,
                "true": int((v == 1).sum()), "false": int((v == 0).sum()), "nulos": nulos}

    if tipo == "fecha":
        fechas = pd.to_datetime(validos)
        if fechas.empty:
            return {"columna": nombre, "tipo": tipo, "min": None, "max": None,
                    "rango_dias": None, "nulos": nulos}
        minimo, maximo = fechas.min(), fechas.max()
        return {"columna": nombre, "tipo": tipo,
                "min": minimo.date().isoformat(), "max": maximo.date().isoformat(),
                "rango_dias": (maximo - minimo).days, "nulos": nulos}

    if tipo == "numerica":
        n = pd.to_numeric(validos, errors="coerce")
        if n.empty:
            return {"columna": nombre, "tipo": tipo, "min": None, "max": None,
                    "promedio": None, "mediana": None, "desviacion_std": None, "nulos": nulos}
        std = _py(n.std())   # con un solo dato es NaN -> None
        return {"columna": nombre, "tipo": tipo,
                "min": _py(n.min()), "max": _py(n.max()),
                "promedio": round(float(n.mean()), 2),
                "mediana": _py(n.median()),
                "desviacion_std": round(std, 2) if std is not None else None,
                "nulos": nulos}

    if tipo == "texto":
        return {"columna": nombre, "tipo": tipo,
                "valores_unicos": int(validos.nunique()), "nulos": nulos}

    # categórica
    conteo = validos.value_counts()   # ordenado de mayor a menor
    return {"columna": nombre, "tipo": tipo,
            "valores_unicos": int(conteo.shape[0]),
            "distribucion": {str(k): int(v) for k, v in conteo.items()},
            "valor_mas_comun": str(conteo.idxmax()),
            "nulos": nulos}


# ===================== ENDPOINT E: PERFIL DUAL =====================
def _serializar(valor):
    """date/datetime -> texto ISO para que se pueda convertir a JSON."""
    return valor.isoformat() if hasattr(valor, "isoformat") else valor


def obtener_perfil(id_registro: int, db) -> dict | None:
    """Busca el mismo id en Mongo (_id) y en MySQL (PK). None si no está en ninguna."""
    doc = coleccion_raw.find_one({"_id": id_registro})
    fila = db.get(PersonajeMaster, id_registro)

    if doc is None and fila is None:
        return None   # el controller responde 404

    vista_sql = (
        {c.name: _serializar(getattr(fila, c.name)) for c in TABLA.columns}
        if fila is not None else None
    )

    respuesta = {"id": id_registro, "vista_mongo": doc, "vista_sql": vista_sql}

    if doc is not None and fila is None:
        respuesta["warning"] = ("Registro existe en Mongo pero no en MySQL. "
                                "Posiblemente no se ha ejecutado /transformar "
                                "o el registro falló en la transformación.")
    elif doc is None and fila is not None:
        respuesta["warning"] = ("Registro existe en MySQL pero no en Mongo. "
                                "Posiblemente se limpió Mongo (reset parcial) "
                                "o el registro fue eliminado del staging.")
    return respuesta