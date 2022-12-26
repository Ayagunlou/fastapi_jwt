from datetime import datetime
from fastapi import Depends, HTTPException, status, APIRouter, Response, UploadFile
from pymongo.collection import ReturnDocument
import shutil
import gridfs
import os
import pathlib
from app import schemas
from app.database import Post,db
from app.oauth2 import require_user
from app.serializers.postSerializers import postEntity, postListEntity,dataList
from bson.objectid import ObjectId
from app.routers.Services.allowed import allowed_file

router = APIRouter()
# File Temp
location = f"{pathlib.Path(__file__).parent.resolve()}/temp/"

@router.get('/')
def get_posts(limit: int = 10, page: int = 1, user_id: str = Depends(require_user)):
    skip = (page - 1) * limit
    pipeline = [
        {'$match': {'user': ObjectId(str(user_id))}},
        {'$lookup': {'from': 'users', 'localField': 'user',
                     'foreignField': '_id', 'as': 'user'}},
        {'$unwind': '$user'},
        {
            '$skip': skip
        }, {
            '$limit': limit
        }
    ]
    posts = postListEntity(Post.aggregate(pipeline))
    return {'status': 'success', 'results': len(posts), 'posts': posts}


@router.post('/', status_code=status.HTTP_201_CREATED)
def create_post(post: schemas.CreatePostSchema, user_id: str = Depends(require_user)):
    post.user = ObjectId(user_id)
    post.created_at = datetime.now().isoformat()
    post.updated_at = post.created_at
    result = Post.insert_one(post.dict())
    pipeline = [
        {'$match': {'_id': result.inserted_id}},
        {'$lookup': {'from': 'users', 'localField': 'user',
                     'foreignField': '_id', 'as': 'user'}},
        {'$unwind': '$user'},
    ]
    new_post = postListEntity(Post.aggregate(pipeline))[0]
    return new_post


@router.put('/{id}')
def update_post(id: str, payload: schemas.UpdatePostSchema, user_id: str = Depends(require_user)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Invalid id: {id}")
    payload.user = ObjectId(user_id)
    updated_post = Post.find_one_and_update(
        {'_id': ObjectId(id),"user":payload.user}, {'$set': payload.dict(exclude_none=True)}, return_document=ReturnDocument.AFTER)
    if not updated_post:
        raise HTTPException(status_code=status.HTTP_200_OK,
                            detail=f'No post with this id: {id} found')
    return postEntity(updated_post)


@router.get('/{id}')
def get_post(id: str, user_id: str = Depends(require_user)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Invalid id: {id}")
    pipeline = [
        {'$match': {'_id': ObjectId(id)}},
        {'$lookup': {'from': 'users', 'localField': 'user',
                     'foreignField': '_id', 'as': 'user'}},
        {'$unwind': '$user'},
    ]
    post = postListEntity(Post.aggregate(pipeline))[0]
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No post with this id: {id} found")
    return post


@router.delete('/{id}')
def delete_post(id: str, user_id: str = Depends(require_user)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Invalid id: {id}")
    post = Post.find_one_and_delete({'_id': ObjectId(id),"user":ObjectId(user_id)})
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'No post with this id: {id} found')
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post('/upload/',status_code=status.HTTP_201_CREATED)
async def upload_files(file:UploadFile | None = None,user_id: str = Depends(require_user)):
        if not file:
            return{"message":"No File Sent"}
        if allowed_file(file.filename):
            time_now = datetime.now()
            time_format = time_now.strftime("%Y%m%d_%H%M%S")
            subtraction,underscore,dot = "-","_","."
            new_file_name = f"{time_format}_{file.filename.replace(subtraction,underscore).replace(dot,underscore,(file.filename.count(dot))-1).lower()}"
        
            with open(f"{location}{new_file_name}","wb") as buffer:
                shutil.copyfileobj(file.file,buffer)
                buffer.close()
                #MongoDB UPLOAD DATA
                file_location = f"{location}{new_file_name}"
                file_data = open(file_location,"rb")
                data = file_data.read()
                file_sent = gridfs.GridFS(db,"file_upload")
                file_sent.put(data=data,filename=new_file_name,Owner=ObjectId(user_id))
            
            return {"Upload":new_file_name}
        else:
            return {"status":"file extension not match"}


@router.get('/upload/')
async def Show_file(): 
    result = db.file_upload.files.find()
    if not result:
        return {"info":"No data"}
    result2 = dataList(result)

    return result2

@router.get('/upload/image/{Idfile}')
async def Show_file_one(Idfile : str): 
    import io
    from fastapi.responses import StreamingResponse
    file_sent = gridfs.GridFS(db,"file_upload")
    outputdata = file_sent.get(file_id=ObjectId(Idfile)).read()
    
    return StreamingResponse(io.BytesIO(outputdata), media_type="image/png")

@router.delete('/upload/',status_code=status.HTTP_202_ACCEPTED)
async def delete_file(filename:str,user_id: str = Depends(require_user)):
    result = db.file_upload.files.find_one_and_delete({"filename":{"$regex":filename},"Owner":ObjectId(user_id)})
    if not result:
        return {"info":"Data Not Find"}
    data_id,data_name = result["_id"],result["filename"]
    delete_data = (db.file_upload.chunks.delete_many({"files_id":ObjectId(data_id)}))
    if delete_data:
        lo_tem = f"{location}{data_name}"
        if os.path.exists(lo_tem):
            os.remove(lo_tem)
        else:
            print("Is Problem")
        return {"info":f"File Deleted {data_name}"}
    else:
        return{"status":"Data Something !!!!!!!!!"}