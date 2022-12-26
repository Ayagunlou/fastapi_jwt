from datetime import datetime, timedelta
import hashlib
from random import randbytes
from bson.objectid import ObjectId
from fastapi import APIRouter, Form, Response, status, Depends, HTTPException,Body,Request
from pydantic import BaseModel, EmailStr, constr

from app import oauth2
from app.database import User
from app.serializers.userSerializers import userEntity, userResponseEntity
from .. import schemas, utils
from app.oauth2 import AuthJWT
from ..config import settings


router = APIRouter()
ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN


@router.post('/register', status_code=status.HTTP_201_CREATED)
async def create_user(payload: schemas.PassCon, request: Request,role:schemas.ModelName):
    # Check if user already exist
    user = User.find_one({'email': payload.email.lower()})
    if user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail='Account already exist')
    # Compare password and passwordConfirm
    if payload.password != payload.passwordConfirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Passwords do not match')
    #  Hash the password
    payload.password = utils.hash_password(payload.password)
    del payload.passwordConfirm
    payload.role = role
    # payload.verified = False
    payload.email = payload.email.lower()
    payload.created_at = datetime.now().isoformat()
    payload.updated_at = payload.created_at
    result = User.insert_one(payload.dict())
    new_user = userResponseEntity(User.find_one({'_id': result.inserted_id}))
    try:
        token = randbytes(10)
        hashedCode = hashlib.sha256()
        hashedCode.update(token)
        verification_code = hashedCode.hexdigest()
        User.find_one_and_update({"_id":result.inserted_id},
            {"$set":{"verification_code": verification_code, "updated_at": datetime.now().isoformat()}})
        url = f"{request.url.scheme}://{request.client.host}:{request.url.port}/api/auth/verifyemail/{token.hex()}"
        f = open('verification.txt', 'a')
        f.write(f"{datetime.now().isoformat()} || Verify Code = {payload.email.lower()} - {token.hex()}\n")  
        f.close()
        print(f"VERIFY CODE = {token.hex()}")
    except Exception as error:
        User.find_one_and_update({"_id": result.inserted_id},
        {"$set": {"verification_code": None, "updated_at": datetime.now().isoformat()}})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail='There was an error sending email')
    return {'status': 'success', 'message': f'Verification token successfully sent to your email {payload.email.lower()}'}

@router.get('/verifyemail/{token}',status_code=status.HTTP_200_OK)
def verify_me(token:str):

    hashedCode = hashlib.sha256()
    hashedCode.update(bytes.fromhex(token))
    verification_code = hashedCode.hexdigest()
    result = User.find_one_and_update({"verification_code": verification_code},
        {"$set":{"verification_code": None, "verified": True, "updated_at": datetime.now().isoformat()}}, new=True)
    if not result:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
         detail='Invalid verification code or account already verified')
    return{"status": "success","message": "Account verified successfully"}

@router.get('/reverify/',status_code=status.HTTP_200_OK)
def verify_re(email:EmailStr):

    token = randbytes(10)
    hashedCode = hashlib.sha256()
    hashedCode.update(token)
    verification_code = hashedCode.hexdigest()
    result = User.find_one_and_update({"email":email.lower(),"verified":False},
        {"$set":{"verification_code": verification_code, "updated_at": datetime.now().isoformat()}})
    if result:
        f = open('verification.txt', 'a')
        f.write("verify"+"= "+email.lower()+" "+token.hex()+"\n")  
        f.close()
        print(f"VERIFY CODE = {token.hex()}")
    elif not result:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
         detail='Invalid verification code or account already verified')
    return{"status": "success","message": "Re - verified successfully"}

# @router.post('/register', status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
# async def create_user(name:str=Form(),email:EmailStr=Form(),password:constr(min_length=8)=Form(),passwordConfirm:str=Form()):
#     # Check if user already exist
#     user = User.find_one({'email': email.lower()})
#     if user:
#         raise HTTPException(status_code=status.HTTP_409_CONFLICT,
#                             detail='Account already exist')
#     # Compare password and passwordConfirm
#     if password != passwordConfirm:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail='Passwords do not match')
#     #  Hash the password
#     password = utils.hash_password(password)
#     user_data = schemas.CreateUserSchema(name=name,
#                                         email=email.lower(),
#                                         password=password,
#                                         role="user",
#                                         created_at=datetime.now().isoformat(),
#                                         updated_at=datetime.now().isoformat(),
#                                         verified=True)
#     result = User.insert_one(user_data.dict())
#     new_user = userResponseEntity(User.find_one({'_id': result.inserted_id}))
#     return {"status": "success", "user": new_user}

@router.post('/login')
# def login(payload: schemas.LoginUserSchema, response: Response, Authorize: AuthJWT = Depends()):
def login(response: Response, Authorize: AuthJWT = Depends(),email:EmailStr=Form(),password:constr(min_length=8)=Form()):
    # Check if the user exist
    # user = userEntity(User.find_one({'email': payload.email.lower()}))
    try:
        user = userEntity(User.find_one({'email': email.lower()}))
    except Exception:
        print("Email Not Find")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Incorrect Email or Password')
    
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Incorrect Email or Password')

    # Check if user verified his email
    if not user['verified']:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Please verify your email address')

    # Check if the password is valid
    # if not utils.verify_password(payload.password, user['password']):
    if not utils.verify_password(password, user['password']):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Incorrect Email or Password')

    # Create access token
    access_token = Authorize.create_access_token(
        subject=str(user["id"]), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN))

    # Create refresh token
    refresh_token = Authorize.create_refresh_token(
        subject=str(user["id"]), expires_time=timedelta(minutes=REFRESH_TOKEN_EXPIRES_IN))

    # Store refresh and access tokens in cookie
    response.set_cookie('access_token', access_token, ACCESS_TOKEN_EXPIRES_IN * 60,
                        ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
    response.set_cookie('refresh_token', refresh_token,
                        REFRESH_TOKEN_EXPIRES_IN * 60, REFRESH_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
    response.set_cookie('logged_in', 'True', ACCESS_TOKEN_EXPIRES_IN * 60,
                        ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, False, 'lax')

    # Send both access
    return {'status': 'success', 'access_token': access_token,'Details':user}


@router.get('/refresh')
def refresh_token(response: Response, Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_refresh_token_required()

        user_id = Authorize.get_jwt_subject()

        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Could not refresh access token')
        user = userEntity(User.find_one({'_id': ObjectId(str(user_id))}))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='The user belonging to this token no logger exist')
        access_token = Authorize.create_access_token(
            subject=str(user["id"]), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN))
    except Exception as e:
        error = e.__class__.__name__
        if error == 'MissingTokenError':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='Please provide refresh token')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    response.set_cookie('access_token', access_token, ACCESS_TOKEN_EXPIRES_IN * 60,
                        ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
    response.set_cookie('logged_in', 'True', ACCESS_TOKEN_EXPIRES_IN * 60,
                        ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, False, 'lax')
    
    return {'access_token': access_token}


@router.get('/logout', status_code=status.HTTP_200_OK)
def logout(response: Response, Authorize: AuthJWT = Depends(), user_id: str = Depends(oauth2.require_user)):
    Authorize.unset_jwt_cookies()
    response.set_cookie('logged_in', '', -1)

    return {'status': 'success'}

@router.delete('/delete/{id}', status_code=status.HTTP_200_OK)
def delete_login_data(response: Response, id: str, Authorize: AuthJWT = Depends(),user_id: str = Depends(oauth2.require_admin)):
    Authorize.unset_jwt_cookies()
    response.set_cookie('logged_in', '', -1)
    User.delete_one({'_id': ObjectId(str(id))})
    return {"status": " delete success"}

@router.put('/update',status_code=status.HTTP_200_OK)
def update_password(response: Response,Authorize: AuthJWT = Depends(),user_id: str = Depends(oauth2.require_user),password:constr(min_length=8)=Form()):
    password = utils.hash_password(password)
    Authorize.unset_jwt_cookies()
    response.set_cookie('logged_in', '', -1)
    User.update_one({'_id': ObjectId(str(user_id))},{'$set':{'password':password,"updated_at": datetime.now().isoformat()}})
    return {"status": "chrange password success"}

@router.post('/test', status_code=status.HTTP_202_ACCEPTED)
def test(payload:schemas.test):
    return {"result":payload}