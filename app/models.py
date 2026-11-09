from pydantic import BaseModel, ConfigDict, Field


class ShipmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: str = Field(min_length=2, max_length=120)
    destination: str = Field(min_length=2, max_length=120)
    recipient: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=2, max_length=500)


class CourierEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventId: str = Field(min_length=4, max_length=120)
    shipmentId: str = Field(min_length=5, max_length=40)
    status: str = Field(min_length=3, max_length=30)
    timestamp: str = Field(min_length=1, max_length=64)