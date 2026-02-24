from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Meal, User
from app.routers.auth import get_current_user
from app.routers.events import broadcast
from app.schemas import MealCreate, MealResponse, MealUpdate

router = APIRouter()


async def _meal_to_response(meal: Meal, db: AsyncSession) -> dict:
    result = await db.execute(select(User).where(User.id == meal.added_by))
    user = result.scalar_one_or_none()
    return MealResponse(
        id=meal.id,
        date=meal.date,
        meal_time=meal.meal_time,
        name=meal.name,
        portion=meal.portion,
        added_by=meal.added_by,
        added_by_name=user.name if user else None,
        updated_at=meal.updated_at,
    ).model_dump()


@router.get("")
async def list_meals(
    week: str | None = Query(None),
    date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if date:
        result = await db.execute(select(Meal).where(Meal.date == date))
    elif week:
        start = datetime.strptime(week, "%Y-%m-%d").date()
        end = start + timedelta(days=6)
        result = await db.execute(
            select(Meal).where(
                and_(Meal.date >= start.isoformat(), Meal.date <= end.isoformat())
            )
        )
    else:
        result = await db.execute(select(Meal))

    meals = result.scalars().all()
    responses = []
    for m in meals:
        responses.append(await _meal_to_response(m, db))
    return responses


@router.post("", response_model=MealResponse)
async def create_meal(
    req: MealCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc).isoformat()
    meal = Meal(
        date=req.date,
        meal_time=req.meal_time,
        name=req.name,
        portion=req.portion,
        added_by=user.id,
        updated_at=now,
    )
    db.add(meal)
    await db.commit()
    await db.refresh(meal)

    resp = await _meal_to_response(meal, db)
    await broadcast("meal_added", resp)
    return resp


@router.put("/{meal_id}", response_model=MealResponse)
async def update_meal(
    meal_id: int,
    req: MealUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Meal).where(Meal.id == meal_id))
    meal = result.scalar_one_or_none()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(meal, field, value)
    meal.updated_at = datetime.now(timezone.utc).isoformat()

    await db.commit()
    await db.refresh(meal)

    resp = await _meal_to_response(meal, db)
    await broadcast("meal_updated", resp)
    return resp


@router.delete("/{meal_id}")
async def delete_meal(
    meal_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Meal).where(Meal.id == meal_id))
    meal = result.scalar_one_or_none()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    meal_data = {"id": meal.id, "date": meal.date, "meal_time": meal.meal_time}
    await db.delete(meal)
    await db.commit()

    await broadcast("meal_deleted", meal_data)
    return {"ok": True}
