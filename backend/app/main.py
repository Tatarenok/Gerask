from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

from app.config import settings
from app.database import init_db, SessionLocal
from app.models.user import Role, User
from app.utils.logger import logger
from app.utils.security import hash_password
from app.routers import auth, tickets, users


async def create_default_roles_and_admin():
    db = SessionLocal()
    try:
        if db.query(Role).count() > 0:
            logger.info("Roles already exist")
            return
        
        roles_data = [
            {"name": "admin", "display_name": "Администратор", "prefix": None, "is_admin": True},
            {"name": "reader", "display_name": "Читатель", "prefix": None, "is_admin": False},
            {"name": "engineer", "display_name": "Инженер (ASU)", "prefix": "ASU", "is_admin": False},
            {"name": "developer", "display_name": "РазраSU", "is_admin": False},
            {"name": "frontend", "display_name": "Фронтендер (FRONTASU)", "prefix": "FRONTASU", "is_admin": False},
            {"name": "tester", "display_name": "Тестировщик (TESTASU)", "prefix": "TESTASU", "is_admin": False},
        ]
        
        for role_data in roles_data:
            db.add(Role(**role_data))
        db.commit()
        
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        db.add(User(
            login="admin",
            password_hash=hash_password("admin"),
            display_name="Администратор",
            role_id=admin_role.id,
        ))
        db.commit()
        logger.info("Default data created")
    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    init_db()
    await create_default_roles_and_admin()
    yiel


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {round((time.time()-start)*1000, 2)}ms")
    return response


app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["Tickets"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])


@app.get("/health")
async def health():
    return {"status": "ok"}
