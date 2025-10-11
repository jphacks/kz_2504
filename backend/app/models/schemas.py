# Data Models
# TODO: Define Pydantic models for API

from pydantic import BaseModel

class SessionCreate(BaseModel):
    # TODO: Define session creation model
    pass

class SyncMessage(BaseModel):
    # TODO: Define sync message model
    current_time: float
    playback_rate: float = 1.0