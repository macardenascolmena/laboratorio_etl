import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import etl_service
from app.views.schemas import (ExtraerRequest, ExtraerResponse, ResetResponse,
                               TransformarResponse)

# Todas las rutas de este archivo empiezan por /api/v1/etl
router = APIRouter(prefix="/api/v1/etl", tags=["ETL"])


@router.post("/extraer", response_model=ExtraerResponse, status_code=201)
def extraer(body: ExtraerRequest):
    if body.cantidad <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor que 0")
    try:
        resultado = etl_service.extraer(body.cantidad)
    except requests.RequestException as e:
        # Falló la API externa: 502 Bad Gateway.
        raise HTTPException(status_code=502, detail=f"Error consultando la API pública: {e}")
    return ExtraerResponse(**resultado, status=201)


@router.post("/transformar", response_model=TransformarResponse, status_code=200)
def transformar(db: Session = Depends(get_db)):
    try:
        resultado = etl_service.transformar_y_cargar(db)
    except etl_service.SinDatosError as e:
        raise HTTPException(status_code=409, detail=str(e))   # falta el paso previo
    return TransformarResponse(**resultado, status=200)


@router.delete("/reset", response_model=ResetResponse, status_code=200)
def reset():
    return ResetResponse(**etl_service.reset(), status=200)