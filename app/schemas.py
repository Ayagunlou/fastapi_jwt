from datetime import datetime
from fastapi import Form
from pydantic import BaseModel, EmailStr, constr,Field
from typing import Optional,List
from bson.objectid import ObjectId
from enum import Enum

class ModelName(str, Enum):
    User = "User"
    Admin = "Admin"
    Owner = "Owner"

class UserBaseSchema(BaseModel):
    name: str
    email: EmailStr
    role: ModelName | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True


class CreateUserSchema(UserBaseSchema):
    password: constr(min_length=8)
    # passwordConfirm: str
    verified: bool = False
class PassCon(CreateUserSchema):
    passwordConfirm: str



class LoginUserSchema(BaseModel):
    email: EmailStr
    password: constr(min_length=8)


class UserResponseSchema(UserBaseSchema):
    id: str
    pass


class UserResponse(BaseModel):
    status: str
    user: UserResponseSchema

class test(BaseModel):
    name: str
    email: EmailStr
    password: constr(min_length=8)
    passwordconfirm: str

class FilteredUserResponse(UserBaseSchema):
    id: str


class PostBaseSchema(BaseModel):
    title: str
    content: str
    category: str
    image: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class CreatePostSchema(PostBaseSchema):
    user: str | None = None
    pass


class PostResponse(PostBaseSchema):
    id: str
    user: FilteredUserResponse
    created_at: datetime
    updated_at: datetime


class UpdatePostSchema(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None
    image: str | None = None
    user: str | None = None

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ListPostResponse(BaseModel):
    status: str
    results: int
    posts: List[PostResponse]

