from pydantic import BaseModel


class LoginRequest(BaseModel):
    pin: str
    user_name: str


class LoginResponse(BaseModel):
    token: str
    user_id: int
    user_name: str


class MealCreate(BaseModel):
    date: str
    meal_time: str
    name: str
    portion: str


class MealUpdate(BaseModel):
    date: str | None = None
    meal_time: str | None = None
    name: str | None = None
    portion: str | None = None


class MealResponse(BaseModel):
    id: int
    date: str
    meal_time: str
    name: str
    portion: str
    added_by: int
    added_by_name: str | None = None
    updated_at: str

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
