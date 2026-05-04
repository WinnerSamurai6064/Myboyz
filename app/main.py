import os, hmac
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Header
from telegram import Update
from app.bot import setup_bot, bot_instance
from app.scheduler import start_active_window


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot_instance.initialize()
    await bot_instance.start()
    yield
    await bot_instance.stop()


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot_instance.bot)
    await bot_instance.update_queue.put(update)
    return {"status": "ok"}


@app.post("/trigger")
async def scheduled_trigger(x_trigger_key: str = Header(None, alias="X-Trigger-Key")):
    expected = os.getenv("TRIGGER_SECRET")
    if not hmac.compare_digest(x_trigger_key or "", expected or ""):
        raise HTTPException(status_code=403)
    await start_active_window()
    return {"status": "active window started"}
