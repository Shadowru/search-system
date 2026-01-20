from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TopicInfo(BaseModel):
    topic_name: str
    role: str
    jira_key: str
    consumer_group: Optional[str] = None