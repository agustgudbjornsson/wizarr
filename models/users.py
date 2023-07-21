from peewee import SQL, CharField, DateTimeField, IntegerField
from pydantic import BaseModel as PydanticBaseModel

from .base import BaseModel


class Users(BaseModel):
    id = IntegerField(primary_key=True)
    token = CharField()  # Plex ID or Jellyfin ID
    username = CharField()
    email = CharField()
    code = CharField()
    expires = DateTimeField(null=True, default=None)
    auth = CharField(null=True, default=None)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])

class UsersModel(PydanticBaseModel):
    id: int
    token: str
    username: str
    email: str
    code: str
    expires: str
    auth: str
    created: str