from __future__ import annotations
from asyncio import Semaphore
from threading import Thread

import requests
from constants import *
from decorators import async_lock
import json
import asyncio
import atexit
import aiohttp
from validate_email import validate_email
from asgiref.sync import async_to_sync


async def main2(client):
    async with aiohttp.ClientSession() as session:
        client.session = session
        while client.alive:
            # print(client.alive)
            now = client.query.copy()
            await asyncio.sleep(0.001)
            client.query = client.query - now
            await asyncio.gather(*now)


def work_with_server(client, loop):
    asyncio.set_event_loop(loop)
    asyncio.run(main2(client))


def modify_url(func):
    def new(self, url, *args, **kwargs):
        return func(self, SERVER + url, *args, **kwargs)

    return new


def login_required(func):
    def new(self: Client, *args, **kwargs):
        if self.user:
            return func(self, *args, **kwargs)
        else:
            return NOT_AUTHORISED

    return new


class Response:

    def __init__(self, text, status):
        self.text = text
        self.status_code = status


class Client:

    def __init__(self):
        self.user: User = None
        self._friends: FriendList = None
        self.query = set()
        self.sessions: SessionList = None
        self.thread = Thread(target=work_with_server, args=(self, asyncio.new_event_loop(),))
        self.get_friends_lock = asyncio.Lock()
        self.login_lock = asyncio.Lock()
        self.logout_lock = asyncio.Lock()
        self.register_lock = asyncio.Lock()
        self.get_sessions_lock = asyncio.Lock()
        self.create_session_lock = asyncio.Lock()
        self.connect_to_session_lock = asyncio.Lock()
        self.disconnect_from_session_lock = asyncio.Lock()
        self.thread.start()
        self.alive = True
        self.current_session: Session = None

    @property
    async def friends(self):
        if not self._friends:
            await self.get_friends()
        return self._friends

    @friends.setter
    def friends(self, value):
        self._friends = value

    @modify_url
    async def post(self, url, data=None, **kwargs):
        async with self.session.post(url, data=data, **kwargs) as response:
            return Response(await response.text(), response.status)
        # return requests.post(url, data, json, **kwargs)

    @modify_url
    async def get(self, url, **kwargs):
        async with self.session.get(url, **kwargs) as response:
            return Response(await response.text(), response.status)

        # return requests.get(url, params, **kwargs)

    @async_lock
    async def register(self, name, email, password):
        if not name:
            return NAME_UNFILLED
        elif not email:
            return EMAIL_UNFILLED
        elif not password:
            return PASSWORD_UNFILLED
        elif not validate_email(email):
            return BAD_EMAIL
        try:
            r = await self.post("/users/create_user",
                                {"name": name, "email": email, "pass": password})
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        err = r.text.rsplit(".")[-1]
        if r.status_code == 200:
            self.user = User(json.loads(r.text))
            self.user.status = ONLINE
            self.add_action(self.get_friends())
            self.add_action(self.get_sessions())
            return 200
        elif err == "email":
            return EMAIL_EXIST
        elif err == "name":
            return NAME_EXIST
        elif err == "Email not valid":
            return BAD_EMAIL
        else:
            return ERROR

    @login_required
    @async_lock
    async def get_friends(self):
        print(self.user.make_headers())
        try:
            r = await self.get("/friends", headers=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            r_j = json.loads(r.text)
            self.friends = FriendList(r_j["confirmed"], r_j["received"], r_j["requested"])
            return 200
        elif r.text == "Wrong password":
            return WRONG_PASSWORD
        elif r.text == "User not exist":
            return USER_NOT_EXIST

    @async_lock
    async def login(self, name, password):
        if not name:
            return NAME_UNFILLED
        elif not password:
            return PASSWORD_UNFILLED
        try:
            r = await self.post("/log_in", headers={"name": name, "pass": password})
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            u = json.loads(r.text)
            u["pass"] = password
            u["status"] = ONLINE
            self.user = User(u)
            self.add_action(self.get_friends())
            self.add_action(self.get_sessions())
            return 200
        elif r.text == "User online":
            return USER_ONLINE
        elif r.text == "Wrong password":
            return WRONG_PASSWORD
        elif r.text == "User not exist":
            return USER_NOT_EXIST

    @login_required
    async def add_friend(self, user):
        if user == self.user:
            return WHAT
        try:
            r = await self.post("/friends/add", {"name": user.name}, headers=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            (await self.friends).add_friend(user)
            return 200
        elif r.text == "You are your friend":
            return WHAT
        elif r.text == "User not exist":
            return USER_NOT_EXIST
        elif r.text == "Friend already added":
            return YOU_FRIENDS
        elif r.text == "Request already sent":
            return FRIEND_REQUEST_EXIST
        elif r.text == "Wrong password":
            return WRONG_PASSWORD
        elif r.text == "User not exist":
            return USER_NOT_EXIST

    @login_required
    async def remove_friend(self, user):
        try:
            r = await self.post("/friends/remove", {"name": user.name},
                                headers=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            (await self.friends).remove_friend(user)
            return 200
        elif r.text == "You are your friend":
            return WHAT
        elif r.text == "User not exist":
            return USER_NOT_EXIST
        elif r.text == "This user not friend":
            return WHO_IS_IT
        elif r.text == "Wrong password":
            return WRONG_PASSWORD
        elif r.text == "User not exist":
            return USER_NOT_EXIST

    @async_lock
    async def get_sessions(self):
        try:
            r = await self.get("/sessions")
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            self.sessions = SessionList(json.loads(r.text))
            return 200
        else:
            print("WHAT")

    async def get_session(self, id):
        try:
            r = await (self.get("/sessions?id=".format(id),
                                headers=self.user.make_headers()) if self.user else self.get(
                "/sessions?id=".format(id)))
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            return Session(json.loads(r.text))
        elif r.status_code == 404:
            return SESSION_NOT_EXIST
        elif r.text == "User not exist":
            return USER_NOT_EXIST
        elif r.text == "Wrong password":
            return WRONG_PASSWORD
        elif r.text == "User offline":
            return USER_OFFLINE

    @login_required
    @async_lock
    async def connect_to_session(self, id):
        try:
            r = await self.post("/sessions/{}/connect".format(id), headers=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            self.current_session = self.sessions[id]
            return 200
        elif r.status_code == 404:
            return SESSION_NOT_EXIST
        elif r.text == "User not exist":
            return USER_NOT_EXIST
        elif r.text == "Wrong password":
            return WRONG_PASSWORD
        elif r.text == "User offline":
            return USER_OFFLINE
        elif r.text == "Game is full":
            return GAME_IS_FULL
        elif r.text == "Game started":
            return GAME_STARTED
        elif r.text == "Game finished":
            return GAME_FINISHED

    @login_required
    @async_lock
    async def create_session(self, name, desc):
        if not name:
            return NAME_UNFILLED
        try:
            r = await self.post("/sessions/create_session", {"name": name, "desc": desc},
                                headers=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            s = json.loads(r.text)
            self.current_session = Session(s)
            return self.current_session
        elif r.text == "User not exist":
            return USER_NOT_EXIST
        elif r.text == "Wrong password":
            return WRONG_PASSWORD
        elif r.text == "User offline":
            return USER_OFFLINE

    @login_required
    @async_lock
    async def disconnect_from_session(self):
        try:
            r = await self.post("/sessions/disconnect", headers=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            self.current_session = None
            return 200
        elif r.text == "User not exist":
            return USER_NOT_EXIST
        elif r.text == "Wrong password":
            return WRONG_PASSWORD
        elif r.text == "User offline":
            return USER_OFFLINE
        elif r.text == "User not in game":
            return USER_NOT_IN_GAME

    @async_lock
    async def logout(self):
        if not self.user:
            return NOT_AUTHORISED
        try:
            await self.post("/log_out", headers=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK

    def add_action(self, action, callback=lambda x: x):
        async def new():
            callback(await action)

        self.query.add(new())


class Session:

    def __init__(self, data=None):
        if data:
            self.id = data["id"]
            self.name = data["name"]
            self.desc = data["desc"]
            self.users_limit = data["limit"]
            self.status = data["status"]
            if data.get("host"):
                self.host = User(data["host"])
            else:
                self.host = None
            self.users = UserList(data["users"])
            self.seed = data["seed"]
        else:
            self.name = self.desc = ""
            self.users_limit = 2
            self.users = UserList()
            self.host = User()
            self.id = self.status = self.seed = None

    def update(self, data):
        if data.get("id") and self.id != data["id"]:
            self.id = data["id"]
        if data.get("name") and self.name != data["name"]:
            self.name = data["name"]
        if data.get("desc") and self.desc != data["desc"]:
            self.desc = data["desc"]
        if data.get("users_limit") and self.users_limit != data["users_limit"]:
            self.users_limit = data["users_limit"]
        if data.get("status") and self.status != data["status"]:
            self.status = data["status"]
        if data.get("users"):
            self.users.update(data["users"])
        if data.get("host"):
            self.host.update(data["host"])
        if data.get("seed") and self.seed != data["seed"]:
            self.seed = data["seed"]


class SessionList(dict):

    def __init__(self, data=None):
        super().__init__()
        if data:
            self.update(data, )

    def update(self, data, **kwargs):
        for s in data:
            self.setdefault(s["id"], Session()).update(s)

    def __repr__(self):
        return "[{}]".format(", ".join(map(str, self.values())))


class FriendList:

    def __init__(self, friends=None, send=None, get=None):
        self.friends = UserList(friends)
        self.s_requests = UserList(send)
        self.g_requests = UserList(get)

    def add_friend(self, other: User):
        if other in self.friends:
            return self
        if other in self.g_requests:
            self.g_requests.remove(other)
            self.friends.add(other)
        elif other not in self.s_requests:
            self.s_requests.add(other)

    def remove_friend(self, other: User):
        if other in self.friends:
            self.friends.remove(other)
        if other in self.s_requests:
            self.s_requests.remove(other)
        if other in self.g_requests:
            self.g_requests.remove(other)

    def __iadd__(self, other: User):
        self.add_friend(other)
        return self

    def __isub__(self, other: User):
        self.remove_friend(other)
        return self


class User:

    def __init__(self, data=None):
        if data:
            self.id = data["id"]
            self.name = data["name"]
            self.password = data.get("pass")
            self.email = data.get("email")
            self.status = data.get("status")
        else:
            self.id = self.name = self.password = self.status = self.email = None

    def update(self, data):
        if data.get("id") and self.id != data["id"]:
            self.id = data["id"]
        if data.get("name") and self.name != data["name"]:
            self.name = data["name"]
        if data.get("email") and self.email != data["email"]:
            self.email = data["name"]
        if data.get("pass") and self.password != data["pass"]:
            self.password = data["pass"]
        if data.get("status") and self.status != data["status"]:
            self.status = data["status"]

    def make_headers(self):
        return {"name": self.name, "pass": self.password}

    def __repr__(self):
        return str(self)

    def __str__(self):
        return '<User "{}" {}>'.format(self.name, "ONLINE" if self.status == ONLINE else "OFFLINE")


class UserList:

    def __init__(self, data=None):
        self.users = {}
        if data:
            self.update(data)

    def __getitem__(self, key):
        return self.users.get(key)

    def __setitem__(self, key, value):
        self.users[key] = value

    def __delitem__(self, key):
        del self.users[key]

    def __contains__(self, user):
        return self.users.get(user.id) or self.users.get(user.name)

    def update(self, data):
        for u in data:
            if u.get("id"):
                self.users.setdefault(u["id"], User()).update(u)
            self.users.setdefault(u["name"], User()).update(u)

    def add(self, user):
        self.users[user.id] = user
        self.users[user.name] = user

    def remove(self, user):
        if user.id and self.users.get(user.id):
            del self.users[user.id]
        del self.users[user.name]

    def __repr__(self):
        return "[{}]".format(", ".join(map(str, set(self.users.values()))))

    def __len__(self):
        return len(self.users) // 2


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
