from fastapi import FastAPI,Request,Depends
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import User
from app.routers import auth, user, post
from app.serializers.userSerializers import userListEntity
from app import oauth2

app = FastAPI()


origins = [
    settings.CLIENT_ORIGIN,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, tags=['Auth'], prefix='/api/auth')
app.include_router(user.router, tags=['Users'], prefix='/api/users')
app.include_router(post.router, tags=['Posts'], prefix='/api/posts')


@app.get("/api/healthchecker")
def root():
    return {"message": "Welcome to FastAPI with MongoDB"}

@app.get("/c")
def all_user():
    result=userListEntity(User.find({}))
    return result

from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
templates = Jinja2Templates(directory="templates")
app.mount("/templates", StaticFiles(directory="templates/static"), name="static")

@app.get('/login',response_class=HTMLResponse)
def page_login(request:Request):
    context ={"request":request}
    return templates.TemplateResponse("login.html",context)
@app.get('/regis',response_class=HTMLResponse)
def page_regis(request:Request):
    context ={"request":request}
    return templates.TemplateResponse("regis.html",context)
@app.get('/page1',response_class=HTMLResponse)
def page_regis(request:Request,user_id: str = Depends(oauth2.require_user)):
    if user_id:
        context ={"request":request}
        return templates.TemplateResponse("page1.html",context)

from app.schemas import ModelName
@app.get('/models/{model}')
async def get_model(model:ModelName):
    if model is model.Owner:
        return {"model_name": model, "message": "Deep Learning FTW!"}

    if model.value == "User":
        return {"model_name": model, "message": "LeCNN all the images"}

    return {"model_name": model, "message": "Have some residuals"}
    


