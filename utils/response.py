from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    code: int
    msg: str
    data: Optional[T] = None

def success(data: Any = None, msg: str = "Success") -> dict:
    return {"code": 200, "msg": msg, "data": data}

def error(code: int = 400, msg: str = "Error", data: Any = None) -> dict:
    return {"code": code, "msg": msg, "data": data}
