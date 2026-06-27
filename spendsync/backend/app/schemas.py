from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    created_at: datetime


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#6366f1", max_length=9)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = Field(default=None, max_length=9)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    updated_at: datetime


class ExpenseCreate(BaseModel):
    amount: float = Field(gt=0)
    currency: str = Field(default="PLN", min_length=3, max_length=3)
    description: str = Field(default="", max_length=255)
    spent_at: date
    category_id: int | None = None
    client_uuid: str | None = Field(default=None, max_length=36)


class ExpenseUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=255)
    spent_at: date | None = None
    category_id: int | None = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: float
    currency: str
    description: str
    spent_at: date
    category_id: int | None
    version: int
    deleted: bool
    client_uuid: str
    updated_at: datetime


class BudgetCreate(BaseModel):
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    limit_amount: float = Field(gt=0)
    category_id: int | None = None


class BudgetUpdate(BaseModel):
    period: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")
    limit_amount: float | None = Field(default=None, gt=0)
    category_id: int | None = None


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period: str
    limit_amount: float
    category_id: int | None
    updated_at: datetime


class BudgetSummary(BaseModel):
    id: int
    period: str
    limit_amount: float
    category_id: int | None
    category_name: str | None
    spent: float
    remaining: float


class SyncChange(BaseModel):
    client_uuid: str = Field(max_length=36)
    amount: float = Field(gt=0)
    currency: str = Field(default="PLN", min_length=3, max_length=3)
    description: str = Field(default="", max_length=255)
    spent_at: date
    category_id: int | None = None
    deleted: bool = False
    base_version: int = 0
    updated_at: datetime | None = None


class SyncPushRequest(BaseModel):
    changes: list[SyncChange]


class SyncResult(BaseModel):
    status: str
    expense: ExpenseOut


class SyncPushResponse(BaseModel):
    server_time: datetime
    results: list[SyncResult]


class SyncPullResponse(BaseModel):
    server_time: datetime
    categories: list[CategoryOut]
    expenses: list[ExpenseOut]
    budgets: list[BudgetOut]
