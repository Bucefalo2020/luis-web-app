import json
from pathlib import Path


BASE_PATH = Path(__file__).resolve().parent.parent


def load_questions_from_json(relative_path: str):
    """
    Carga preguntas desde un archivo JSON dentro del proyecto.
    
    :param relative_path: Ruta relativa desde la raíz del proyecto.
    :return: Lista de preguntas.
    """
    file_path = BASE_PATH / relative_path
    
    if not file_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data
