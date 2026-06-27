from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/categories", tags=["categories"])


def _get_owned(db: Session, user: models.User, category_id: int) -> models.Category:
    category = db.scalar(
        select(models.Category).where(
            models.Category.id == category_id,
            models.Category.user_id == user.id,
        )
    )
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


@router.get("", response_model=list[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    stmt = select(models.Category).where(models.Category.user_id == user.id).order_by(models.Category.name)
    return db.scalars(stmt).all()


@router.post("", response_model=schemas.CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    category = models.Category(user_id=user.id, name=payload.name, color=payload.color)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=schemas.CategoryOut)
def update_category(
    category_id: int,
    payload: schemas.CategoryUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    category = _get_owned(db, user, category_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    category = _get_owned(db, user, category_id)
    db.delete(category)
    db.commit()
