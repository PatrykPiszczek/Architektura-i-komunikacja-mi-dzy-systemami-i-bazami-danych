from datetime import date
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/expenses", tags=["expenses"])


def _check_category(db: Session, user: models.User, category_id: int | None) -> None:
    if category_id is None:
        return
    owned = db.scalar(
        select(models.Category).where(
            models.Category.id == category_id,
            models.Category.user_id == user.id,
        )
    )
    if owned is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


def _get_owned(db: Session, user: models.User, expense_id: int) -> models.Expense:
    expense = db.scalar(
        select(models.Expense).where(
            models.Expense.id == expense_id,
            models.Expense.user_id == user.id,
            models.Expense.deleted.is_(False),
        )
    )
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@router.get("", response_model=list[schemas.ExpenseOut])
def list_expenses(
    category_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    stmt = select(models.Expense).where(
        models.Expense.user_id == user.id,
        models.Expense.deleted.is_(False),
    )
    if category_id is not None:
        stmt = stmt.where(models.Expense.category_id == category_id)
    if date_from is not None:
        stmt = stmt.where(models.Expense.spent_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(models.Expense.spent_at <= date_to)
    if min_amount is not None:
        stmt = stmt.where(models.Expense.amount >= min_amount)
    if max_amount is not None:
        stmt = stmt.where(models.Expense.amount <= max_amount)
    if q:
        stmt = stmt.where(models.Expense.description.ilike(f"%{q}%"))
    stmt = stmt.order_by(models.Expense.spent_at.desc(), models.Expense.id.desc())
    return db.scalars(stmt).all()


@router.post("", response_model=schemas.ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _check_category(db, user, payload.category_id)
    expense = models.Expense(
        user_id=user.id,
        client_uuid=payload.client_uuid or str(uuid4()),
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        spent_at=payload.spent_at,
        category_id=payload.category_id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/{expense_id}", response_model=schemas.ExpenseOut)
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return _get_owned(db, user, expense_id)


@router.put("/{expense_id}", response_model=schemas.ExpenseOut)
def update_expense(
    expense_id: int,
    payload: schemas.ExpenseUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    expense = _get_owned(db, user, expense_id)
    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data:
        _check_category(db, user, data["category_id"])
    for key, value in data.items():
        setattr(expense, key, value)
    expense.version += 1
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    expense = _get_owned(db, user, expense_id)
    expense.deleted = True
    expense.version += 1
    db.commit()
