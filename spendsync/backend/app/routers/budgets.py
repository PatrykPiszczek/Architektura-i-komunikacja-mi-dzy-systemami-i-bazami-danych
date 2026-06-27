from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _get_owned(db: Session, user: models.User, budget_id: int) -> models.Budget:
    budget = db.scalar(
        select(models.Budget).where(
            models.Budget.id == budget_id,
            models.Budget.user_id == user.id,
        )
    )
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget


@router.get("", response_model=list[schemas.BudgetOut])
def list_budgets(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    stmt = select(models.Budget).where(models.Budget.user_id == user.id).order_by(models.Budget.period.desc())
    return db.scalars(stmt).all()


@router.get("/summary", response_model=list[schemas.BudgetSummary])
def budget_summary(
    period: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    stmt = select(models.Budget).where(models.Budget.user_id == user.id)
    if period is not None:
        stmt = stmt.where(models.Budget.period == period)
    budgets = db.scalars(stmt).all()

    summaries = []
    for budget in budgets:
        expense_stmt = select(models.Expense).where(
            models.Expense.user_id == user.id,
            models.Expense.deleted.is_(False),
        )
        if budget.category_id is not None:
            expense_stmt = expense_stmt.where(models.Expense.category_id == budget.category_id)
        expenses = db.scalars(expense_stmt).all()
        spent = float(
            sum(e.amount for e in expenses if e.spent_at.strftime("%Y-%m") == budget.period)
        )
        category_name = budget.category.name if budget.category is not None else None
        summaries.append(
            schemas.BudgetSummary(
                id=budget.id,
                period=budget.period,
                limit_amount=float(budget.limit_amount),
                category_id=budget.category_id,
                category_name=category_name,
                spent=spent,
                remaining=float(budget.limit_amount) - spent,
            )
        )
    return summaries


@router.post("", response_model=schemas.BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: schemas.BudgetCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    budget = models.Budget(
        user_id=user.id,
        period=payload.period,
        limit_amount=payload.limit_amount,
        category_id=payload.category_id,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.put("/{budget_id}", response_model=schemas.BudgetOut)
def update_budget(
    budget_id: int,
    payload: schemas.BudgetUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    budget = _get_owned(db, user, budget_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(budget, key, value)
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    budget = _get_owned(db, user, budget_id)
    db.delete(budget)
    db.commit()
