from fastapi import Depends, FastAPI, status, UploadFile, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo import MongoClient
from requests import get
from emoji import is_emoji
import jwt
from os import getenv

secret = getenv('secret')
database = getenv('db')

app = FastAPI()
mongo = MongoClient(database)
db = mongo["nm-games"]

origins = [
    "http://localhost:5173"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

oauth2_scheme = HTTPBearer(bearerFormat="string")
stories = db['stories']
about_me = db['about_me']


class Story(BaseModel):
    player: int
    time: int
    emotes: dict = {}


class AboutMe(BaseModel):
    content: str


class User(BaseModel):
    sub: int
    name: str


class Signin(BaseModel):
    name: str
    token: str


class Reaction(BaseModel):
    emoji: str
    gamer: int


def get_user(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    payload = jwt.decode(token.credentials.encode(), secret, algorithms=["HS256"])

    return User(**payload)


@app.post('/authenticate')
def authenticate(details: Signin):
    response = get(f"https://api.nm-games.eu/verify/{details.name}/{details.token}").json()

    if not response['correct']:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={details: "invalid_token"})

    gamer = get(f"https://api.nm-games.eu/player/{details.name}").json()
    user = User(sub=gamer['id'], name=gamer['name'])
    return {"token": jwt.encode(user.dict(), secret, algorithm="HS256")}


@app.get('/profile/{user_id}')
def get_profile(user_id: str):
    gamer = get(f"https://api.nm-games.eu/player/{user_id}").json()
    final_result = {
        "gamer": gamer
    }
    if gamer["story"]["has_story"]:
        result = stories.find_one({
            "player": gamer["id"],
            "time": gamer["story"]["post_time"]
        })
        if result:
            story = Story(**result)
        else:
            story = Story(player=gamer["id"], time=gamer["story"]["post_time"])
            stories.insert_one(story.dict())
        final_result["story"] = story.dict()
    else:
        stories.delete_many({
            "player": gamer["id"]
        })

    about_result = about_me.find_one({
        "player": gamer["id"]
    })
    if about_result:
        final_result["about_me"] = about_result["content"]

    return final_result


@app.post('/react')
def react(reaction: Reaction, user: User = Depends(get_user)):
    if not is_emoji(reaction.emoji):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"details": "invalid_emoji"})

    gamer = get(f"https://api.nm-games.eu/player/{reaction.gamer}").json()
    if not gamer["story"]["has_story"]:
        return JSONResponse(status_code=status.HTTP_417_EXPECTATION_FAILED, content={"details": "no_story"})

    result = stories.find_one({
        "player": gamer["id"],
        "time": gamer["story"]["post_time"]
    })
    if result:
        story = Story(**result)
    else:
        story = Story(player=gamer["id"], time=gamer["story"]["post_time"])
        stories.insert_one(story.dict())

    if reaction.emoji not in story.emotes:
        story.emotes[reaction.emoji] = []

    if user.name in story.emotes[reaction.emoji]:
        story.emotes[reaction.emoji].remove(user.name)
        if len(story.emotes[reaction.emoji]) == 0:
            del story.emotes[reaction.emoji]
    else:
        story.emotes[reaction.emoji].append(user.name)

    stories.update_one({
        "player": gamer["id"],
        "time": gamer["story"]["post_time"]
    }, {"$set": story.dict()})

    return story


@app.post('/about')
def set_about_me(about: AboutMe, user: User = Depends(get_user)):
    result = about_me.find_one({
        "player": user.sub
    })
    if result:
        about_me.update_one({
            "player": user.sub
        }, {"$set": {"content": about.dict()}})
    else:
        about_me.insert_one({
            "player": user.sub,
            "content": about.dict()
        })

    return {}
