from pydantic import BaseModel
from typing import Optional


class VerifyConsultantRequest(BaseModel):
    decision: str        # "approve" | "reject"
    note: Optional[str] = None
