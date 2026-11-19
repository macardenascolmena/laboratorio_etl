from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.controllers import analitica_controller, etl_controller
from app.database import Base, engine
from app.models import entidad_sql  # noqa: F401  (importarlo registra la tabla en Base.metadata)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Corre una vez al arrancar: crea la tabla si no existe.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Laboratorio ETL - FastAPI", version="1.0.0", lifespan=lifespan)

# Registra los dos grupos de rutas.
app.include_router(etl_controller.router)
app.include_router(analitica_controller.router)