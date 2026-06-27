from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/changes", response_model=schemas.SyncPullResponse)
def pull_changes(
    since: datetime | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    server_time = datetime.now(timezone.utc)

    def changed(model):
        stmt = select(model).where(model.user_id == user.id)
        if since is not None:
            stmt = stmt.where(model.updated_at > since)
        return db.scalars(stmt).all()

    return schemas.SyncPullResponse(
        server_time=server_time,
        categories=changed(models.Category),
        expenses=changed(models.Expense),
        budgets=changed(models.Budget),
    )


def _apply(expense: models.Expense, change: schemas.SyncChange) -> None:
    expense.amount = change.amount
    expense.currency = change.currency
    expense.description = change.description
    expense.spent_at = change.spent_at
    expense.category_id = change.category_id
    expense.deleted = change.deleted


def _as_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.post("/push", response_model=schemas.SyncPushResponse)
def push_changes(
    payload: schemas.SyncPushRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    results = []
    for change in payload.changes:
        existing = db.scalar(
            select(models.Expense).where(
                models.Expense.user_id == user.id,
                models.Expense.client_uuid == change.client_uuid,
            )
        )

        if existing is None:
            expense = models.Expense(
                user_id=user.id,
                client_uuid=change.client_uuid,
                amount=change.amount,
                currency=change.currency,
                description=change.description,
                spent_at=change.spent_at,
                category_id=change.category_id,
                deleted=change.deleted,
                version=1,
            )
            db.add(expense)
            db.flush()
            results.append(schemas.SyncResult(status="created", expense=schemas.ExpenseOut.model_validate(expense)))
            continue

        if change.base_version == existing.version:
            _apply(existing, change)
            existing.version += 1
            db.flush()
            results.append(schemas.SyncResult(status="updated", expense=schemas.ExpenseOut.model_validate(existing)))
            continue

        client_wins = change.updated_at is not None and _as_aware(change.updated_at) > _as_aware(existing.updated_at)
        if client_wins:
            _apply(existing, change)
            existing.version += 1
            db.flush()
            status = "conflict_client_won"
        else:
            status = "conflict_server_won"
        results.append(schemas.SyncResult(status=status, expense=schemas.ExpenseOut.model_validate(existing)))

    db.commit()
    return schemas.SyncPushResponse(server_time=datetime.now(timezone.utc), results=results)
