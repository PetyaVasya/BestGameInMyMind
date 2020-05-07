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
from collections import deque


async def main2(client):
    async with aiohttp.ClientSession() as session:
        client.session = session
        while client.alive:
            # print(client.alive)
            now = client.query.copy()
            await asyncio.sleep(0.001)
            client.query = client.query - now
            for coro in now:
                asyncio.create_task(coro)
            # await asyncio.gather(*now)
        await client.refresh()
        await client.logout()


def work_with_server(client, loop):
    asyncio.set_event_loop(loop)
    asyncio.run(main2(client))


def modify_url(func):
    def new(self, url, *args, **kwargs):
        return func(self, SERVER + "/api" + url, *args, **kwargs)

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

    def __str__(self):
        return "<Response {} '{}'>".format(self.status_code, self.text)

    def __repr__(self):
        return "<Response {} '{}'>".format(self.status_code, self.text)


class Client:

    def __init__(self):
        self.alive = True
        self.user: User = None
        self._friends: FriendList = None
        self.query = set()
        self.sessions: SessionList = SessionList()
        self.thread = Thread(target=work_with_server, args=(self, asyncio.new_event_loop(),))
        self.get_friends_lock = asyncio.Lock()
        self.login_lock = asyncio.Lock()
        self.logout_lock = asyncio.Lock()
        self.register_lock = asyncio.Lock()
        self.get_sessions_lock = asyncio.Lock()
        self.create_session_lock = asyncio.Lock()
        self.connect_to_session_lock = asyncio.Lock()
        self.disconnect_from_session_lock = asyncio.Lock()
        self.start_session_lock = asyncio.Lock()
        self.get_actions_lock = asyncio.Lock()
        self.surrender_lock = asyncio.Lock()
        self.refresh_lock = asyncio.Lock()
        self.thread.start()
        self.current_session: Session = None
        self.callbacks = {}
        self.callbacks_semaphores = {}
        self.session = None

    @property
    def friends(self):
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
            # self.user = User(json.loads(r.text))
            # self.add_action(self.get_friends())
            # self.add_action(self.get_sessions())
            return 200
        elif err == "email":
            return EMAIL_EXIST
        elif err == "name":
            return NAME_EXIST
        elif err == "Email not valid":
            return BAD_EMAIL
        elif r.status_code == 401:
            return SERVER_DONT_WORK
        else:
            return ERROR

    @login_required
    @async_lock
    async def get_friends(self):
        try:
            r = await self.get("/friends", auth=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            r_j = json.loads(r.text)
            self.friends = FriendList(r_j["confirmed"], r_j["received"], r_j["requested"])
            return 200
        elif r.status_code == 401:
            return SERVER_DONT_WORK
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
            r = await self.post("/log_in", auth=aiohttp.BasicAuth(name, password))
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            if not self.user:
                u = json.loads(r.text)
                self.user = User(u)
                self.add_action(self.get_friends())
                self.add_action(self.get_sessions())
            return 200
        elif r.status_code == 401:
            return 401
        elif r.text == "User online":
            return USER_ONLINE
        elif r.text == "Wrong password":
            return WRONG_PASSWORD
        elif r.text == "User not exist":
            return USER_NOT_EXIST

    @async_lock
    async def refresh(self):
        if not self.user:
            return USER_NOT_EXIST
        try:
            r = await self.post("/token", auth=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            if not self.user:
                u = json.loads(r.text)
                self.user = User(u)
            else:
                u = json.loads(r.text)
                if u.get("session_hash"):
                    self.user.password = u["session_hash"]
            return 200
        elif r.status_code == 401:
            return 401
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
            r = await self.post("/friends/add", {"name": user.name},
                                auth=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            (await self.friends).add_friend(user)
            return 200
        elif r.status_code == 401:
            return SERVER_DONT_WORK
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
                                auth=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            (await self.friends).remove_friend(user)
            return 200
        elif r.status_code == 401:
            return SERVER_DONT_WORK
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
            r = await (
                self.get("/sessions", auth=self.user.make_headers()) if self.user else self.get(
                    "/sessions"))
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            # print(r.text)
            self.sessions.update(json.loads(r.text))
            if self.current_session:
                for i in self.sessions:
                    if i == self.current_session:
                        self.current_session = i
            return 200
        elif r.status_code == 401:
            return SERVER_DONT_WORK
        else:
            print("WHAT")

    async def get_session(self, id):
        try:
            r = await (self.get("/sessions?id={}".format(id),
                                auth=self.user.make_headers()) if self.user else self.get(
                "/sessions?id={}".format(id)))
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            s = Session(json.loads(r.text))
            if self.current_session and s == self.current_session:
                self.current_session = s
            return s
        elif r.status_code == 401:
            return SERVER_DONT_WORK
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
            r = await self.post("/sessions/{}/connect".format(id), auth=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            self.current_session = self.sessions[id]
            return 200
        elif r.status_code == 401:
            return SERVER_DONT_WORK
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
        elif r.text == "You in this session":
            self.current_session = self.sessions[id]
            return 200

    @login_required
    @async_lock
    async def create_session(self, name, desc):
        if not name:
            return NAME_UNFILLED
        try:
            r = await self.post("/sessions/create_session", {"name": name, "desc": desc},
                                auth=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            s = json.loads(r.text)
            self.current_session = Session(s)
            return self.current_session
        elif r.status_code == 401:
            return SERVER_DONT_WORK
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
            r = await self.post("/sessions/disconnect", auth=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK
        if r.status_code == 200:
            self.current_session = None
            return 200
        elif r.status_code == 401:
            return SERVER_DONT_WORK
        elif r.text == "User not exist":
            return USER_NOT_EXIST
        elif r.text == "Wrong password":
            return WRONG_PASSWORD
        elif r.text == "User offline":
            return USER_OFFLINE
        elif r.text == "User not in game":
            return USER_NOT_IN_GAME

    @login_required
    @async_lock
    async def start_session(self):
        r = await self.post("/sessions/{}/start".format(self.current_session.id),
                            auth=self.user.make_headers())
        if r.status_code == 200:
            return 200
        elif r.status_code == 401:
            return SERVER_DONT_WORK
        elif r.status_code == 200:
            pass

    @async_lock
    async def logout(self):
        if not self.user:
            return NOT_AUTHORISED
        try:
            await self.post("/log_out", auth=self.user.make_headers())
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK

    async def apply_action(self, name, data):
        return await self.post("/sessions/{}/action/{}".format(self.current_session.id, name),
                               json={"data": data},
                               auth=self.user.make_headers())

    @login_required
    async def make_path(self, start, points_removed, points_added):
        try:
            res = await self.apply_action("make_path",
                                          {"path": start, "removed": points_removed,
                                           "added": points_added})
            if res.status_code == 200:
                return 200
            elif res.status_code == 404:
                return 404
            elif res.status_code == 401:
                return SERVER_DONT_WORK
            try:
                return json.loads(res.text)
            except Exception as e:
                print(e)
                return 400
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK

    @login_required
    async def build(self, hexagon, build_type, player, attrs):
        try:
            data = {"x": hexagon[0],
                    "y": hexagon[1],
                    "type": BUILDING,
                    "player": player,
                    "attributes":
                        {
                            "struct": build_type
                        }}
            data["attributes"].update(attrs)
            res = await self.apply_action("build", data)
            if res.status_code == 200:
                return 200
            elif res.status_code == 404:
                return 404
            elif res.status_code == 401:
                return SERVER_DONT_WORK
            print(type(res.text))
            try:
                return json.loads(res.text)
            except Exception as e:
                print(e)
                return 400
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK

    @login_required
    async def destroy_building(self, hexagon):
        try:
            res = await self.apply_action("destroy",
                                          {"hexagon": hexagon})
            if res.status_code == 200:
                return 200
            elif res.status_code == 404:
                return 404
            elif res.status_code == 401:
                return SERVER_DONT_WORK
            try:
                return json.loads(res.text)
            except Exception as e:
                print(e)
                return 400
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK

    @login_required
    @async_lock
    async def get_actions(self):
        try:
            res = await self.get("/sessions/{}/changes".format(self.current_session.id),
                                 auth=self.user.make_headers())
            try:
                return json.loads(res.text)
            except:
                return 400
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK

    @login_required
    @async_lock
    async def surrender(self):
        try:
            res = await self.post("/sessions/{}/surrender".format(self.current_session.id),
                                  auth=self.user.make_headers())
            if res.status_code == 200:
                return 200
            elif res.status_code == 401:
                return SERVER_DONT_WORK
            return 200
        except aiohttp.ClientConnectionError:
            return SERVER_DONT_WORK

    def add_action(self, action, callback=lambda x: x, lock_callback=False):
        name = str(action.__qualname__)

        if name == "get_session" or name == "add_friend" or name == "remove_friend"\
                or name == "name":

            async def new():

                try:
                    r = await action
                except TypeError:
                    r = action
                if r != STILL_RUNNING:
                    now = self.callbacks[name]
                    await asyncio.sleep(0.001)
                    for f in now:
                        f(r)
                    self.callbacks[name] -= now

            self.callbacks.setdefault(name, set()).add(callback)

        else:
            async def new():
                if lock_callback:
                    async with self.callbacks_semaphores.setdefault(name, asyncio.Semaphore(1)):
                        try:
                            callback(await action)
                        except TypeError:
                            callback(action)
                else:
                    try:
                        callback(await action)
                    except TypeError:
                        callback(action)

        self.query.add(new())

    @property
    def current_player(self):
        if self.current_session is None:
            return None
        return self.current_session.users.index(self.user)


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
                self.host = User()
            self.users = UserList(data["users"])
            self.seed = data.get("seed")
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
        if data.get("limit") and self.users_limit != data["limit"]:
            self.users_limit = data["limit"]
        if data.get("status") and self.status != data["status"]:
            self.status = data["status"]
        if self.status == S_PENDING:
            if data.get("users"):
                self.users.update(data["users"])
        if data.get("host"):
            self.host.update(data["host"])
        if data.get("seed") and self.seed != data["seed"]:
            self.seed = data["seed"]

    def __eq__(self, other):
        return isinstance(other, Session) and self.id == other.id


class SessionList(dict):

    def __init__(self, data=None):
        super().__init__()
        if data:
            self.update(data)

    def update(self, data, **kwargs):
        # self.clear()
        r_keys = set(self.keys()) - set(map(lambda x: x.get("id"), data))
        for s in data:
            self.setdefault(s["id"], Session(s)).update(s)
        for k in r_keys:
            del self[k]

    def __repr__(self):
        return "[{}]".format(", ".join(map(str, self.values())))

    def __iter__(self):
        return iter(self.values())

    def to_list(self):
        return list(self.values())


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
            self.password = data.get("session_hash")
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
        if data.get("status") and self.status != data["status"]:
            self.status = data["status"]

    def make_headers(self):
        return aiohttp.BasicAuth(self.password if self.password else "", "unused")

    def __repr__(self):
        return str(self)

    def __str__(self):
        return '<User "{}" {}>'.format(self.name, "ONLINE" if self.status == ONLINE else "OFFLINE")

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        elif isinstance(other, User):
            return self.name == other.name
        else:
            raise TypeError("Only User or str")

    def __hash__(self):
        return hash(self.name)


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

    def __iter__(self):
        return iter(set(self.users.values()))

    def index(self, value):
        return list(self.users.values()).index(value) // 2

    def index_by_name(self, name):
        for ind, u in enumerate(self.users.values()):
            if u.name == name:
                return ind // 2
        return -1

    def update(self, data):
        r_keys = set(self.users.keys()) - set(map(lambda x: x.get("id"), data)) - set(
            map(lambda x: x.get("name"), data))
        for u in data:
            if u.get("id"):
                self.users.setdefault(u["id"], User()).update(u)
            self.users.setdefault(u["name"], User()).update(u)
        for k in r_keys:
            del self[k]

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

    def to_list(self):
        a = []
        for k in self.users.keys():
            if isinstance(k, str):
                a.append(self.users[k])
        return a


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
