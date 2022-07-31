import urllib.parse

import aiohttp
from aiohttp import InvalidURL, ClientConnectorError
from fastapi import FastAPI, BackgroundTasks, Header, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.utils import get_db, get_redis_server


app = FastAPI()


@app.on_event("startup")
async def startup_event():
    db = await get_db()
    redis_server = await get_redis_server()
    async for document in db.Urls.find({}):
        await redis_server.set(document["path"], document["url"])


@app.on_event("shutdown")
async def shutdown_event():
    db = await get_db()
    redis_server = await get_redis_server()
    async for document in db.Urls.find({}):
        await redis_server.delete(document["path"])


async def add_to_redis_server(db_document):
    redis_server = await get_redis_server()
    await redis_server.set(db_document["path"], db_document["url"])


app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


@app.get("/")
async def home():
    return FileResponse("./frontend/index.html")


@app.post("/add-url")
async def add_url(csrf_token: str = Header(...), path: str = Form(...), redirect_url: str = Form(...),  # skipcq: PYL-W0613
                  db=Depends(get_db), redis_server=Depends(get_redis_server)):

    initial_url = redirect_url
    if "http://" not in redirect_url:
        if "https://" not in redirect_url:
            redirect_url = "http://" + redirect_url

    try:
        async with aiohttp.ClientSession() as session, session.get(redirect_url) as response:  # skipcq: PYL-W0612
            pass
    except InvalidURL:
        raise HTTPException(status_code=400, detail="Not a valid url.")
    except ClientConnectorError:
        raise HTTPException(status_code=400, detail="Not a valid url.")

    safe_path = urllib.parse.quote(path, safe="/")

    if await db.Urls.find_one({"path": safe_path}):
        raise HTTPException(status_code=400, detail="Path already in use.")

    await db.Urls.insert_one({"path": safe_path, "url": redirect_url})
    await redis_server.set(safe_path, redirect_url)

    return {"message": "Successfully added shortened url.", "redirect_url": initial_url, "path": safe_path}


@app.get("/{path}")
async def redirect(path,  background_tasks: BackgroundTasks, db=Depends(get_db), redis_server=Depends(get_redis_server)):
    safe_path = urllib.parse.quote(path, safe="/")
    redirect_url = await redis_server.get(safe_path)
    if redirect_url is None:
        redirect_url_document = await db.Urls.find_one({"path": path})
        if redirect_url_document is None:
            raise HTTPException(status_code=404, detail="Not a valid path.")
        else:
            background_tasks.add_task(add_to_redis_server, redirect_url_document)
            return RedirectResponse(redirect_url_document["url"])
    else:
        return RedirectResponse(str(redirect_url)[2:-1])
