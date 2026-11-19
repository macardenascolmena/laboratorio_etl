from pydantic import BaseModel, Field


class ExtraerRequest(BaseModel):
    # La regla cantidad > 0 se valida en el controller para responder 400
    # (con Field(gt=0) la respuesta sería 422).
    cantidad: int = Field(..., examples=[50], description="Cuántos personajes descargar")


class ExtraerResponse(BaseModel):
    mensaje: str
    nuevos: int
    ya_existentes: int
    fuente: str
    status: int


class TransformarResponse(BaseModel):
    mensaje: str
    registros_procesados: int
    tabla_destino: str
    status: int


class ResetResponse(BaseModel):
    mensaje: str
    mongo_docs_eliminados: int
    mysql_rows_eliminadas: int
    status: int