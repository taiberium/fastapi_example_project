from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Query-string pagination DTO, used as a FastAPI dependency.

    FastAPI maps its scalar fields to query params (`?skip=&limit=`) — this is
    request input, not a JSON body.
    """

    skip: int = Field(0, ge=0)
    limit: int = Field(10, gt=0)
