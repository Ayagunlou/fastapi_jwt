from app.serializers.userSerializers import embeddedUserResponse


def postEntity(post) -> dict:
    return {
        "id": str(post["_id"]),
        "title": post["title"],
        "category": post["category"],
        "content": post["content"],
        "image": post["image"],
        "user": str(post["user"]),
        "created_at": post["created_at"],
        "updated_at": post["updated_at"]
    }


def populatedPostEntity(post) -> dict:
    return {
        "id": str(post["_id"]),
        "title": post["title"],
        "category": post["category"],
        "content": post["content"],
        "image": post["image"],
        "user": embeddedUserResponse(post["user"]),
        "created_at": post["created_at"],
        "updated_at": post["updated_at"]
    }


def postListEntity(posts) -> list:
    return [populatedPostEntity(post) for post in posts]

def convert(data) -> dict:
        return {
            "id":str(data["_id"]),
            "filename":data["filename"],
            "size_byte":data["length"],
            "uploadDate":data["uploadDate"],
            "Owner":str(data["Owner"])
        }
def dataList(users) -> list:
        return [convert(user) for user in users]
