from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Pydantic model representing the overall application health status."""

    status: str = Field(
        ...,
        description="The current status of the application.",
        examples=["healthy"],
    )
    service: str = Field(
        ...,
        description="The service name.",
        examples=["mycommunity-api"],
    )
    version: str = Field(
        ...,
        description="The running version of the application.",
        examples=["1.0.0"],
    )


class DatabaseHealthResponse(BaseModel):
    """Pydantic model representing the database connectivity health status."""

    status: str = Field(
        ...,
        description="The status of the database connectivity.",
        examples=["healthy", "unhealthy"],
    )
    database: str = Field(
        ...,
        description="The detail of database connectivity.",
        examples=["connected", "disconnected"],
    )
