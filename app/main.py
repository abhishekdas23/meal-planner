from contextlib import asynccontextmanager

import bcrypt
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.config import settings
from app.database import engine, async_session
from app.models import Base, User, Household
from app.routers import auth, meals, events


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Seed users
        for name in settings.user_names:
            existing = await session.execute(select(User).where(User.name == name))
            if not existing.scalar_one_or_none():
                session.add(User(name=name))

        # Seed household PIN
        existing_hh = await session.execute(select(Household))
        if not existing_hh.scalar_one_or_none():
            pin_hash = bcrypt.hashpw(
                settings.household_pin.encode(), bcrypt.gensalt()
            ).decode()
            session.add(Household(id=1, pin_hash=pin_hash))

        await session.commit()

    yield

    await engine.dispose()


app = FastAPI(title="Meal Planner", lifespan=lifespan)

app.include_router(auth.router, prefix="/api/auth")
app.include_router(meals.router, prefix="/api/meals")
app.include_router(events.router, prefix="/api")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")
