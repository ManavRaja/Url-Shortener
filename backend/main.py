import datetime
import urllib.parse

import aiohttp
from aiohttp import InvalidURL, ClientConnectorError
from dateutil.relativedelta import relativedelta
from fastapi import FastAPI, BackgroundTasks, Header, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse

from backend.utils import get_db, get_redis_server

app = FastAPI()


async def add_to_redis_server(db_document):
    redis_server = await get_redis_server()
    await redis_server.set(db_document["path"], db_document["url"])


@app.post("/add-url")
async def add_url(csrf_token: str = Header(...), path: str = Form(...), redirect_url: str = Form(...),
                  db=Depends(get_db), redis_server=Depends(get_redis_server)):

    safe_path = urllib.parse.quote(path, safe="/")

    if path[0] != "/":
        raise HTTPException(status_code=400, detail="Not a path.")
    elif await db.Urls.find_one({"path": safe_path}):
        raise HTTPException(status_code=400, detail="Path already in use.")

    try:
        async with aiohttp.ClientSession() as session, session.get(redirect_url) as response:
            pass
    except InvalidURL:
        raise HTTPException(status_code=400, detail="Not a valid url.")
    except ClientConnectorError:
        raise HTTPException(status_code=400, detail="Not a valid url.")

    await db.Urls.insert_one({"path": safe_path, "url": redirect_url,
                              "expiry_date": datetime.datetime.utcnow() + relativedelta(years=1)})
    await redis_server.set(safe_path, redirect_url)

    return {"message": "Successfully added shortened url."}


@app.get("/{path}")
async def redirect(path,  background_tasks: BackgroundTasks, db=Depends(get_db), redis_server=Depends(get_redis_server)):
    redirect_url = await redis_server.get("/" + path)
    if redirect_url is None:
        redirect_url_document = await db.Urls.find_one({"path": "/" + path})
        if redirect_url_document is None:
            raise HTTPException(status_code=404, detail="Not a valid path.")
        else:
            background_tasks.add_task(add_to_redis_server, redirect_url_document)
            return RedirectResponse(redirect_url_document["url"])
    else:
        return RedirectResponse(str(redirect_url)[2:-1])
