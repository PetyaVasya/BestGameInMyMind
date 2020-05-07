import asyncio
import inspect
from collections import deque
from itertools import islice

import pygame
import Game
import json
import UI
import ptext
import sys
import platform

from Client import Session, User, SessionList
from Environment import Path
from constants import *


def main():
    pygame.init()
    pygame.font.init()
    g = Game.Game()
    ch = pygame.display.Info().current_h
    g.STANDARD_FONT = int(g.STANDARD_FONT * 800 / ch)
    g.STATUSBAR_FONT = int(g.STATUSBAR_FONT * 800 / ch)
    pygame.display.set_caption("TVOI GIMN")
    size = width, height = 800, 600
    # if platform.system() == "Darwin":
    #     screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    # else:
    #     screen = pygame.display.set_mode((0, 0))
    screen = pygame.display.set_mode(size)
    i_size = screen.get_size()
    size = pygame.Vector2(i_size)
    running = True
    clock = pygame.time.Clock()
    screen_system = UI.ScreensSystem(screen)

    g.screen = screen_system
    g.surface = screen
    g.init_pygame_variables()

    def go_solo():
        screen_system.current = "loading"

        async def create_fight():
            g.create_fight()

        def go_offline(x):
            screen_system.current = "offline"

        g.client.add_action(create_fight(), go_offline)

    def go_online():
        if g.client.user:
            log_form.clear()
            reg_form.clear()
            create_session_form.clear()
            screen_system.current = "online"
            g.client.add_action(g.client.get_sessions(), set_sessions)
            g.client.add_action(g.client.get_sessions(), update_current_session)
        else:
            screen_system.current = "login"

    def go_main():
        log_form.clear()
        reg_form.clear()
        create_session_form.clear()
        screen_system.current = "main"

    def lost_server_connection():
        c = g.client
        c.user = None
        c.sessions = SessionList()
        c.friends = None
        c.current_session = None
        if g.session:
            g.session.ended = True
        sessions_frame.current = "Все лобби"
        current_sess_btn.active = False
        create_btn.active = True
        if screen_system.current != "offline":
            d = UI.Dialog(screen_system.overlay.surface, "Вы потеряли соединение с сервером",
                          OK_BUTTON,
                          "Потеряно соединение", align=CENTER, width=220, height=220)
            screen_system.overlay.add_object(pygame.Vector2(), d)

            go_main()

    def go_settings():
        screen_system.current = "settings"

    def log_cancel():
        for f in log_form.fields:
            if isinstance(f, UI.InputField):
                f.text = ""
        for f in reg_form.fields:
            if isinstance(f, UI.InputField):
                f.text = ""
        screen_system.current = "main"

    def finish():
        client = Game.Game().client

        def die(x=None):
            client.alive = False

        if client.user:
            client.add_action(client.logout(), die)
        else:
            die()
        sys.exit()

    def login(form, x):
        c = Game.Game().client

        def parse_login(y):
            print(y)
            if y == 200:
                log_form.clear()
                go_online()
                update_friends(200)
                refresh_token(200)
            elif y == 401:
                form.error.text = "Неправильные данные, либо вы не подтвердили почту"
            elif y == SERVER_DONT_WORK:
                form.error.text = "Не удается получить доступ к серверу"
            elif y == USER_ONLINE:
                form.error.text = "Пользователь уже в сети"

        c.add_action(c.login(x["name"], x["pass"]), parse_login)

    def update_friends(x):
        c = g.client
        if x == 200:
            if c.user:
                async def updf():
                    try:
                        await asyncio.sleep(10)
                        return await c.get_friends()
                    except TypeError:
                        pass
                c.add_action(updf(), update_friends)

    def refresh_token(x):
        c = g.client
        if x == 200:
            if c.user:
                async def rfsh():
                    try:
                        await asyncio.sleep(540)
                        return await c.refresh()
                    except TypeError:
                        pass
                c.add_action(rfsh(), refresh_token)

    def register(form, x):

        def parse_reg(y):
            if y == 200:
                reg_form.clear()
                login_btn.click()
                s = UI.Dialog(screen_system.overlay.surface,
                              "Вы успешно зарегестрировались. Пожалуйста, подтвердите ваш аккаунт"
                              " (ссылка на почте).",
                              title="Успешная регистрация", buttons=OK_BUTTON, width=350,
                              height=210,
                              align=CENTER)
                screen_system.overlay.add_object(pygame.Vector2(), s)
            elif y == NAME_UNFILLED:
                form.error.text = "Заполните поле 'имя'"
            elif y == BAD_EMAIL:
                form.error.text = "Неверная почта"
            elif y == PASSWORD_UNFILLED:
                form.error.text = "Заполните поле 'пароль'"
            elif y == WRONG_PASSWORD:
                form.error.text = "Неправильный пароль"
            elif y == USER_NOT_EXIST:
                form.error.text = "Такого пользователя не существует"
            elif y == SERVER_DONT_WORK:
                form.error.text = "Не удается получить доступ к серверу"
            elif y == EMAIL_UNFILLED:
                form.error.text = "Заполните поле 'почта'"
            elif y == EMAIL_EXIST:
                form.error.text = "Пользователь с такой почтой существует"
            elif y == NAME_EXIST:
                form.error.text = "Пользователь с таким именем существует"

        c = Game.Game().client
        c.add_action(c.register(x["name"], x["email"], x["pass"]), parse_reg)

    def go_session(session: Session):
        create_session_form.clear()
        users_in_session.set_data([{"user": i} for i in session.users.to_list()])
        current_sess_btn.click()
        current_sess_btn.active = True
        create_btn.active = False

    def update_game(x):
        c = g.client

        if not g.session:
            c.current_session = None
            return
        if x == SERVER_DONT_WORK:
            lost_server_connection()
            return
        elif not isinstance(x, int):
            for action in x:
                if action["action"] == "SURRENDER":
                    print("SURRENDER:", "{} сдался".format(action["player"]))
                    t = UI.Toast(screen_system.overlay.surface,
                                 "{} сдался".format(action["player"]), 2, "Противник сдался",
                                 width=200, height=100, align=TOP_RIGHT)
                    screen_system.overlay.add_object(pygame.Vector2(), t)
                elif action["action"] == "BUILD":
                    print("BUILD:", action["data"])
                    g.session.field.convert_map({"hexagons": [action["data"]]})
                    hexagon: Game.Project = g.session.field.get_hexagon(action["data"]["x"],
                                                                        action["data"]["y"])
                    hexagon.hp += 1
                    if Game.UnitSpawn in hexagon.building.__class__.__bases__ or isinstance(
                            hexagon.building, Game.UnitSpawn):
                        hexagon.building.alpha = 0.15
                    hexagon.sprite.set_alpha(255)
                elif action["action"] == "MAKE_PATH":
                    data = action["data"]
                    print("MAKE PATH:", data)
                    start = g.session.field.get_hexagon(*data["path"])
                    if isinstance(start, Game.Project):
                        g.session.field.set_hexagon(start.building)
                        start = start.building
                    new_points = []
                    for p in data["added"]:
                        new_points.append(tuple(p))
                    start.path = Path(deque(list(islice(start.path.points, 0,
                                                        len(start.path.points) - data[
                                                            "removed"])) + new_points), start.player)
                elif action["action"] == "WIN":
                    print("WIN:", action["player"])
                    if g.session and g.client.user == action["player"]:
                        g.end_game(True)
                    else:
                        g.end_game(False)
                    c.current_session = None
                    return
                elif action["action"] == "FIELD_CREATED":
                    print("FIELD ON SERVER CREATED")
                    g.screen.current = "game"
                elif action["action"] == "DESTROY":
                    if g.session and g.session.field.map[action["data"]["hexagon"]]:
                        del g.session.field.map[action]
                else:
                    print("WTF")

        async def new():
            await asyncio.sleep(0.1)
            return await c.get_actions()

        c.add_action(new(), update_game, lock_callback=True)

    def update_current_session(x):
        c = g.client
        if x == 200:
            s = c.current_session
            if s:
                if s.status == STARTED and s.seed:
                    print("GAME STARTEDDDDDDDDDDD")
                    g.screen.current = "loading"
                    current_sess_btn.active = False
                    create_btn.active = True
                    sessions_frame.current = "Все лобби"
                    g.create_fight(seed=s.seed, player=c.current_player + 1, players=len(s.users))
                    c.add_action(c.get_actions(), update_game, lock_callback=True)
                    return
                else:
                    if s.host == c.user:
                        start_game_btn.active = True
                    else:
                        start_game_btn.active = False
                    users_in_session.set_data([{"user": i} for i in s.users.to_list()])
        elif x == SERVER_DONT_WORK:
            lost_server_connection()
            return
        set_sessions(200)

        async def new():

            await asyncio.sleep(0.2)
            return await c.get_sessions()

        c.add_action(new(), update_current_session)

    background = pygame.transform.scale(pygame.image.load(BACKGROUNDS[MAIN]).convert_alpha(),
                                        i_size)
    main_screen = UI.Screen(size)
    main_screen.add_object(pygame.Vector2(), UI.Image(None, background))
    login_screen = UI.Screen(size)
    login_screen.add_object(pygame.Vector2(), UI.Image(None, background))
    online_screen = UI.Screen(size)
    online_screen.add_object(pygame.Vector2(), UI.Image(None, background))
    settings_screen = UI.Screen(size)
    lobby_screen = UI.Screen(size)
    game_screen = UI.Screen(size)
    load_screen = UI.Screen(size)
    load_screen.add_object(pygame.Vector2(), UI.AnimatedImage(None, Game.load_image_set(
        "./images/anim_sets/loading_screen", scale=i_size)))

    # Main screen elements
    start_btn_list = UI.DataLayout(main_screen.surface, size.x * 0.4, size.y,
                                   base_color=TRANSPARENT(),
                                   v_align=BETWEEN, h_align=MIDDLE)
    start_btn_list.add_element(
        UI.Button(None).set_background(UI.Text(None, "Одиночная игра")).set_action(go_solo))
    start_btn_list.add_element(
        UI.Button(None).set_background(UI.Text(None, "Сетевая игра")).set_action(go_online))
    start_btn_list.add_element(
        UI.Button(None).set_background(UI.Text(None, "Выход")).set_action(finish))

    main_screen.add_object(pygame.Vector2(size.x * 0.6, 0), start_btn_list)
    start_btn_list.move_elements()

    l1 = UI.DataLayout(None, *size, border=0, base_color=TRANSPARENT(), h_align=MIDDLE,
                       v_align=CENTER)
    login_screen.add_object(pygame.Vector2(), l1)
    log_reg_frame = UI.Frame(None, width=600, height=500, btns_pos=TOP)
    l1.add_element(log_reg_frame)
    # login_screen.add_object(pygame.Vector2(100, 50), log_reg_frame)
    log_form = UI.Form(login_screen.surface, width=590, height=441, btns_pos=BOTTOM)
    reg_form = UI.Form(login_screen.surface, width=590, height=441, btns_pos=BOTTOM)
    login_btn = log_reg_frame.append("Log in", log_form)
    log_reg_frame.append("Register", reg_form)

    cancel = UI.Button(login_screen.surface).set_background(UI.Text(None, "Cancel")).set_action(
        log_cancel)
    log_form.fields.v_align = CENTER
    log_form.add_field(UI.Text(login_screen.surface, "Name:", fsize=40))
    log_form.add_field(UI.InputField(login_screen.surface, width=log_form.inner_rect.w), "name")
    log_form.add_field(UI.Text(login_screen.surface, "Password:", fsize=40))
    log_form.add_field(
        UI.InputField(login_screen.surface, width=log_form.inner_rect.w, v_type=UI.PasswordType),
        "pass")
    log_form.add_btn(cancel)
    log_form.add_btn(
        UI.Button(login_screen.surface).set_background(UI.Text(None, "ОК")).set_action(
            lambda: login(log_form, log_form.result)))

    reg_form.fields.v_align = CENTER
    reg_form.add_field(UI.Text(login_screen.surface, "Name:", fsize=40))
    reg_form.add_field(UI.InputField(login_screen.surface, width=reg_form.inner_rect.w), "name")
    reg_form.add_field(UI.Text(login_screen.surface, "Email:", fsize=40))
    reg_form.add_field(UI.InputField(login_screen.surface, width=reg_form.inner_rect.w), "email")
    reg_form.add_field(UI.Text(login_screen.surface, "Password:", fsize=40))
    reg_form.add_field(
        UI.InputField(login_screen.surface, width=reg_form.inner_rect.w, v_type=UI.PasswordType),
        "pass")
    reg_form.add_btn(cancel)
    reg_form.add_btn(
        UI.Button(login_screen.surface).set_background(UI.Text(None, "ОК")).set_action(
            lambda: register(reg_form, reg_form.result)))

    l2 = UI.DataLayout(None, *size, border=0, base_color=TRANSPARENT(), h_align=MIDDLE,
                       v_align=CENTER)
    online_screen.add_object(pygame.Vector2(), l2)
    sessions_frame = UI.Frame(None, size.x * 0.7, size.y, btns_pos=LEFT)
    l2.add_element(sessions_frame)
    surf = pygame.Surface(((size.x * 0.5 - 10) * 0.9, max((size.y - 10) * 0.2, 100)))
    surf.fill(BASE_COLOR)
    view = UI.DataElement()

    def connect_to_session(x: Session):
        c = Game.Game().client
        if c.user in x.users:
            go_session(x)
            return

        def new(y):
            if y == 200:
                go_session(x)
            elif y == SESSION_NOT_EXIST or y == GAME_FINISHED:
                s = UI.Dialog(screen_system.overlay.surface, "Лобби уже не существует",
                              title="Ошибка подключения", buttons=OK_BUTTON, width=210, height=210,
                              align=CENTER)
                screen_system.overlay.add_object(pygame.Vector2(), s)
                c.add_action(c.get_sessions(), set_sessions)
            elif y == GAME_IS_FULL:
                s = UI.Dialog(screen_system.overlay.surface, "Лобби заполенно",
                              title="Ошибка подключения", buttons=OK_BUTTON, width=210, height=210,
                              align=CENTER)
                screen_system.overlay.add_object(pygame.Vector2(), s)
                c.add_action(c.get_sessions(), set_sessions)
            elif y == GAME_STARTED:
                s = UI.Dialog(screen_system.overlay.surface, "Игра уже началась",
                              title="Ошибка подключения", buttons=OK_BUTTON, width=210, height=210,
                              align=CENTER)
                screen_system.overlay.add_object(pygame.Vector2(), s)
                c.add_action(c.get_sessions(), set_sessions)

        c.add_action(c.connect_to_session(x.id), new)

    view.set_action(lambda x: connect_to_session(x.session))
    view.set_background(surf)

    def set_sessions(y):
        if y == 200:
            new_data = [{"session": i} for i in g.client.sessions.to_list()]
            if new_data != recycle_view.data:
                print("seted")
                recycle_view.set_data(new_data)
            if not g.client.friends:
                return
            friend_new_data = [{"session": i} for i in g.client.sessions.to_list() if
                               any(map(lambda x: x in g.client.friends.friends, i.users))]
            if friend_new_data != friend_recycle_view.data:
                print("friend seted")
                friend_recycle_view.set_data(friend_new_data)

    def draw_session(x, y: Session):
        ptext.draw(y.name, (5, 5), width=x.get_width() - 10, surf=x,
                   align="center")
        ptext.draw(y.desc, (5, 30), width=x.get_width() - 55, surf=x)
        ptext.draw("{}/{}".format(len(y.users), y.users_limit),
                   pygame.Vector2((size.x * 0.5 - 10) * 0.9 - 50, 30), surf=x)

    view.view_data = {"session": draw_session}
    recycle_view = UI.DataRecycleView(online_screen.surface, *sessions_frame.elements_rect.size,
                                      pos=pygame.Vector2(0, 0))
    friend_recycle_view = UI.DataRecycleView(online_screen.surface,
                                             *sessions_frame.elements_rect.size,
                                             pos=pygame.Vector2(0, 0))

    current_session = UI.DataLayout(online_screen.surface, *sessions_frame.elements_rect.size,
                                    orientation=VERTICAL)
    current_sess_btn = sessions_frame.append("Текущее лобби", current_session)
    current_sess_btn.active = False

    users_in_session = UI.DataRecycleView(online_screen.surface, current_session.data_rect.w,
                                          current_session.data_rect.h * 0.9)

    surf2 = pygame.Surface((users_in_session.data_rect.w, 50))
    surf2.fill(BASE_COLOR // 2)
    users_view = UI.DataElement(online_screen.surface)
    users_view.set_background(surf2)

    def draw_user(x, y: User):
        c = Game.Game().client
        ptext.draw(y.name, (5, 5), width=x.get_width() - 10, surf=x,
                   align="center")
        if c.current_session:
            if y == c.current_session.host:
                ptext.draw("HOST", (55, 30), width=x.get_width() - 55, surf=x)

    users_view.view_data = {"user": draw_user}
    users_in_session.set_view(users_view)
    current_session.add_element(users_in_session)
    current_session_btns = UI.DataLayout(online_screen.surface, current_session.data_rect.w,
                                         current_session.data_rect.h * 0.1, border=0,
                                         orientation=HORIZONTAL, h_align=BETWEEN, v_align=MIDDLE)
    current_session.add_element(current_session_btns)

    def disconnect_from_lobby():
        c = Game.Game().client

        def callback(y):
            if y == 200:
                c.add_action(c.get_sessions(), set_sessions)

            else:
                print(y)
                go_session(c.current_session)

        current_sess_btn.active = False
        all_lobbies.click()
        create_btn.active = True
        c.add_action(c.disconnect_from_session(), callback)

    sessions_frame.append("Все лобби", recycle_view)
    all_lobbies = sessions_frame.btns[-1]
    create_session_form = UI.Form(online_screen.surface, *sessions_frame.elements_rect.size,
                                  pos=pygame.Vector2(0, 0), btns_pos=BOTTOM)
    create_session_form.fields.v_align = CENTER
    create_session_form.add_field(UI.Text(screen, "Название:", fsize=40))
    create_session_form.add_field(
        UI.InputField(online_screen.surface, width=create_session_form.elements_rect.w, limit=20),
        "name")
    create_session_form.add_field(UI.Text(screen, "Описание:", fsize=40))
    create_session_form.add_field(
        UI.MultiLineField(online_screen.surface, width=create_session_form.elements_rect.w), "desc")
    create_session_form.add_btn(
        UI.Button(online_screen.surface).set_background(UI.Text(None, "Отмена")).set_action(
            lambda: all_lobbies.get_click(all_lobbies.world_position))
    )

    def create_session(form, x):
        c = Game.Game().client

        def parse_create_session(y):
            print(y, "CREATED")
            if isinstance(y, Session):
                c.add_action(c.get_sessions(), set_sessions)
                go_session(y)
                create_session_form.clear()
            elif y == NAME_UNFILLED:
                form.error.text = "Заполните поле 'имя'"

        print(x)
        c.add_action(c.create_session(x["name"], x["desc"]), parse_create_session)

    def start_game():
        g = Game.Game()
        c = g.client
        s = c.current_session
        if len(s.users) > 1 and s.host == c.user:
            c.add_action(c.start_session())

    create_session_form.add_btn(
        UI.Button(online_screen.surface).set_background(UI.Text(None, "ОК")).set_action(
            lambda: create_session(create_session_form, create_session_form.result)))

    create_btn = sessions_frame.append("Создать лобби", create_session_form)
    current_session_btns.add_element(
        UI.Button(None).set_background(UI.Text(None, "Выход")).set_action(disconnect_from_lobby))
    start_game_btn = UI.Button(None).set_background(UI.Text(None, "Начать игру")).set_action(
        start_game)
    start_game_btn.active = False
    current_session_btns.add_element(start_game_btn)

    sessions_frame.append("Лобби друзей", friend_recycle_view)
    sessions_frame.add_btn(
        UI.Button(None).set_background(UI.Text(None, "Назад")).set_action(go_main))
    recycle_view.set_view(view)
    friend_recycle_view.set_view(view)
    all_lobbies.click()

    screen_system.add_screen("main", main_screen)
    screen_system.add_screen("login", login_screen)
    screen_system.add_screen("online", online_screen)
    screen_system.add_screen("settings", settings_screen)
    screen_system.add_screen("lobby", lobby_screen)
    screen_system.add_screen("game", game_screen)
    screen_system.add_screen("loading", load_screen)
    screen_system.current = "main"
    while running:
        screen.fill(pygame.Color("black"))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

                def gg(x):
                    g.client.alive = False
                    if g.session:
                        g.session.ended = True

                if g.session and g.session.mode == ONLINE and not g.session.ended:
                    async def new():
                        await g.client.refresh()
                        return await g.client.surrender()
                    g.client.add_action(new(), gg)
                else:
                    gg(1)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                screen_system.get_click(pygame.Vector2(event.pos))
            elif event.type == pygame.KEYDOWN:
                screen_system.k_down(event)
        pressed = pygame.key.get_pressed()
        screen_system.check_pressed(pressed)
        g.tick(clock.tick(FPS) / 1000)
        g.flip()
        pygame.display.flip()


if __name__ == "__main__":
    main()
