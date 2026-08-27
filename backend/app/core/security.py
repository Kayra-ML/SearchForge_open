import re
from fastapi import HTTPException

DRIVE_FILE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]{10,100}$')
MAX_QUERY_LENGTH = 200
MIN_QUERY_LENGTH = 1


def validate_file_id(file_id: str) -> str:
    if not file_id or not DRIVE_FILE_ID_PATTERN.match(file_id):
        raise HTTPException(status_code=400, detail="Invalid file ID format")
    return file_id


def validate_search_query(q: str) -> str:
    q = q.strip()
    if len(q) < MIN_QUERY_LENGTH:
        raise HTTPException(status_code=400, detail="Query too short")
    if len(q) > MAX_QUERY_LENGTH:
        raise HTTPException(status_code=400, detail="Query too long")
    return q


def sanitize_error_message(message: str) -> str:
    sensitive_patterns = [
        r'service.account.*\.json',
        r'/[a-z0-9_\-/]*credentials[a-z0-9_\-/]*',
        r'private_key["\s:]+[^\s,}]+',
        r'client_email["\s:]+[^\s,}]+',
    ]
    for pattern in sensitive_patterns:
        message = re.sub(pattern, '[REDACTED]', message, flags=re.IGNORECASE)
    return message