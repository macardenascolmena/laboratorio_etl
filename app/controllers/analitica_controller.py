from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import analitica_service

# Todas las rutas de este archivo empiezan por /api/v1/analitica
router = APIRouter(prefix="/api/v1/analitica", tags=["Analítica"])


@router.get("/columna/{nombre}")
def analizar_columna(nombre: str):
    validas = analitica_service.columnas_validas()
    # 400 con la lista de columnas válidas, como exige el PDF.
    if nombre not in validas:
        raise HTTPException(
            status_code=400,
            detail={"mensaje": f"La columna '{nombre}' no existe", "columnas_validas": validas},
        )
    try:
        return analitica_service.analizar_columna(nombre)
    except analitica_service.TablaVaciaError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/perfil/{id_registro}")
def perfil_dual(id_registro: int, db: Session = Depends(get_db)):
    perfil = analitica_service.obtener_perfil(id_registro, db)
    if perfil is None:   # no existe en ninguna base
        raise HTTPException(status_code=404, detail=f"El id {id_registro} no existe en Mongo ni en MySQL")
    return perfil