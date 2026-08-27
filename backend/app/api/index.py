from fastapi import APIRouter
from app.services.index_service import get_connection, get_index_status, init_db

router = APIRouter()


@router.get("/index/status")
def index_status():
    init_db()
    conn = get_connection()
    try:
        return get_index_status(conn)
    finally:
        conn.close()