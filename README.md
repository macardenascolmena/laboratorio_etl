# Laboratorio Final (2) — Pipeline ETL con FastAPI

Pipeline ETL que descarga personajes de la **Rick & Morty API**, los guarda crudos en **MongoDB** (staging) y los carga limpios en **MySQL** (data warehouse), con endpoints de analítica.

## División de responsabilidades

Este laboratorio fue desarrollado de forma **individual** por:

| Integrante | Responsabilidad |
|---|---|
| Manuel Araujo Cardenas Colmenares | Todo el proyecto: conexiones, modelo SQL, ETL (extraer, transformar, reset), analítica (columna y perfil dual), repositorio y documentación |

## Arquitectura

Fuente (API pública) → Staging (MongoDB) → Data Warehouse (MySQL)

- `app/controllers`: rutas HTTP, sin lógica de negocio.
- `app/services`: lógica del ETL y de la analítica.
- `app/models`: tabla SQL con SQLAlchemy.
- `app/views`: esquemas Pydantic.

## Instalación

```
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

1. Copiar `.env.example` como `.env` y completar las credenciales.
2. Crear la base en MySQL: `CREATE DATABASE laboratorio_etl CHARACTER SET utf8mb4;`
3. Tener MongoDB corriendo en `localhost:27017`.

## Ejecución

```
uvicorn app.main:app --reload
```

Documentación interactiva en `http://127.0.0.1:8000/docs`.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/etl/extraer` | Descarga personajes y los guarda en Mongo con el id de la API como `_id` (idempotente) |
| POST | `/api/v1/etl/transformar` | Aplana y limpia con Pandas y carga en MySQL con upsert (idempotente) |
| DELETE | `/api/v1/etl/reset` | Borra los documentos de Mongo y hace `TRUNCATE` en MySQL |
| GET | `/api/v1/analitica/columna/{nombre}` | Análisis estadístico según el tipo de la columna, detectado dinámicamente |
| GET | `/api/v1/analitica/perfil/{id}` | El mismo registro visto en Mongo y en MySQL |

## Tabla `personajes_master`

La PK `id_personaje` es igual al `_id` de Mongo y no es autoincremental. Tiene 11 columnas: `id_personaje`, `nombre`, `status`, `species`, `subtipo`, `genero`, `origen_nombre`, `ubicacion_nombre`, `total_episodios`, `esta_vivo` y `fecha_creacion`.

## Decisiones de diseño

- **Idempotencia:** en Mongo con `ReplaceOne(upsert=True)`; en MySQL con `INSERT ... ON DUPLICATE KEY UPDATE`.
- **Nulos:** los textos se rellenan con `N/A`; los numéricos y las fechas quedan como `NULL`.
- **Reset:** usa `TRUNCATE`, no `DROP`, para conservar la tabla.
- **Analítica:** el tipo se lee del modelo de SQLAlchemy, sin nombres de columna escritos a mano.