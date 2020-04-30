import asyncio
import re

import discord
import typing

from discord.ext import commands
import json
import aiohttp
from discord.ext.commands import BadArgument

from exceptions import *

bot = commands.Bot(command_prefix="!")

try:
    with open("settings.json") as r:
        settings = json.load(r)
except FileNotFoundError:
    print("Вы не создали файл settings.json с полями token, api и server_id")
    exit()
guild: discord.Guild = None


def str_to_name(s):
    return "-".join(s.lower().split())


async def get_top(count=10):
    try:
        async with aiohttp.ClientSession() as session:
            return await (
                await session.get(settings["api"] + "/api/top", params={"count": count})).json()
    except aiohttp.ClientConnectionError:
        raise ServerNotResponded


async def get_posts(count=100):
    try:
        async with aiohttp.ClientSession() as session:
            return await (
                await session.get(settings["api"] + "/api/posts", params={"count": count})).json()
    except aiohttp.ClientConnectionError:
        raise ServerNotResponded


async def update_top():
    top_channel: discord.TextChannel = discord.utils.get(guild.text_channels, name="топ")
    if not top_channel:
        raise ChannelNotExist
    top_msg: discord.Message = (await top_channel.history(limit=1).flatten())
    if not top_msg or not top_msg[0].embeds:
        embed: discord.Embed = discord.Embed()
        embed.title = "ТОП-10"
        embed.description = "Топ 10 игроков нашей игры"
    else:
        embed = top_msg[0].embeds[0]
        embed.clear_fields()
    embed.colour = discord.Colour.dark_gold()
    top = await get_top()
    embed.add_field(name="Игроки", value="\n".join(
        "{}: {} / {} побед".format(ind, "{} ({})".format(user["name"], guild.get_member(
            user["discord"]).mention) if user.get("discord") else user["name"], user["wins"]) for
        ind, user in enumerate(top, 1)), inline=False)
    if top_msg:
        await top_msg[0].edit(embed=embed)
    else:
        await top_channel.send(embed=embed)


async def get_user(name):
    try:
        async with aiohttp.ClientSession() as session:
            return await (
                await session.get(settings["api"] + "/api/users/{}".format(name))).json()
    except aiohttp.ClientConnectionError:
        raise ServerNotResponded
    except aiohttp.ContentTypeError:
        raise ServerCode404


async def get_friends(name):
    try:
        async with aiohttp.ClientSession() as session:
            return await (await session.get(settings["api"] + "/api/friends",
                                            auth=aiohttp.BasicAuth(settings["token"], ""),
                                            params={"user-name": name})).json()
    except aiohttp.ClientConnectionError:
        raise ServerNotResponded
    except aiohttp.ContentTypeError:
        raise ServerCode404


_utils_get = discord.utils.get


class UUserConverter(commands.UserConverter):

    async def convert(self, ctx, argument) -> discord.User:
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)
        result = None
        state = ctx._state
        if match is not None:
            user_id = int(match.group(1))
            result = ctx.bot.get_user(user_id) or _utils_get(ctx.message.mentions, id=user_id)
        else:
            arg = argument

            # Remove the '@' character if this is the first character from the argument
            if arg[0] == '@':
                # Remove first character
                arg = arg[1:]

            # check for discriminator if it exists,
            if len(arg) > 5 and arg[-5] == '#':
                discrim = arg[-4:]
                name = arg[:-5]
                predicate = lambda u: u.name == name and u.discriminator == discrim
                result = discord.utils.find(predicate, state._users.values())
                if result is not None:
                    return result

            # predicate = lambda u: u.name == arg
            # result = discord.utils.find(predicate, state._users.values())

        if result is None:
            raise BadArgument('User "{}" not found'.format(argument))

        return result


class RandomThings(commands.Cog):

    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.command(name="make_fast_news")
    @commands.has_permissions(administrator=True)
    async def send_news(self, ctx: commands.Context, title: str, *, description: str):
        await ctx.message.delete(delay=300)
        t_channel: discord.TextChannel = discord.utils.get(guild.text_channels, name="новости")
        if not t_channel:
            await ctx.send("Извините, но канала с новостями не существует",
                           delete_after=300)
            return
        embed = discord.Embed()
        embed.title = title
        embed.description = description
        embed.add_field(name="Теги", value="#Срочные новости")
        await t_channel.send(embed=embed)

    # @commands.command(name='roll_dice')
    # async def roll_dice(self, ctx, count):
    #     res = [random.choice(dashes) for _ in range(int(count))]
    #     await ctx.send(" ".join(res))
    #
    # @commands.command(name='randint')
    # async def my_randint(self, ctx, min_int, max_int):
    #     num = random.randint(int(min_int), int(max_int))
    #     await ctx.send(num)

    @commands.command(name="update_top")
    @commands.has_permissions(administrator=True)
    async def update_top(self, ctx: commands.Context):
        try:
            await update_top()
        except ChannelNotExist:
            await ctx.send("Извините, но канала 'топ' не существует", delete_after=300)
        await ctx.message.delete(delay=300)

    @commands.command(name="top")
    async def top(self, ctx: commands.Context):
        await ctx.message.delete(delay=300)
        embed: discord.Embed = discord.Embed()
        embed.title = "ТОП-100"
        embed.description = "Топ 100 игроков нашей игры"
        embed.colour = discord.Colour.gold()
        top = await get_top(100)
        embed.add_field(name="Игроки", value="\n".join(
            "{}: {} / {} побед".format(ind, "{} | <@!{}>".format(user["name"],
                                                                 user["discord"]) if user.get(
                "discord") else user["name"], user["wins"])
            for
            ind, user in enumerate(top, 1)), inline=False)
        await ctx.author.send(embed=embed)

    @commands.command(name="site")
    async def site(self, ctx):
        embed = discord.Embed()
        embed.title = "Наш сайт"
        embed.colour = discord.Colour.orange()
        embed.set_footer(settings["api"])
        await ctx.send(embed=embed)

    @commands.command(name="link")
    async def link(self, ctx: commands.Context):
        embed = discord.Embed()
        embed.title = "Ссылка для привязки"
        embed.colour = discord.Colour.dark_blue()
        embed.set_footer(settings["api"] + "/discord/login")
        await ctx.author.send(embed=embed)

    @commands.command(name="place")
    async def place(self, ctx: commands.Context, user: typing.Union[UUserConverter, str]):
        await ctx.message.delete(delay=300)
        embed = discord.Embed()
        embed.colour = discord.Colour.greyple()
        embed.title = "Позиция игрока"
        try:
            if isinstance(user, (discord.Member, discord.User)):
                cuser = await get_user(user.id)
                embed.add_field(name="Дискорд", value=user.mention)
            elif isinstance(user, str):
                cuser = await get_user(user)
        except ServerCode404:
            await ctx.send("Извините, но такой пользователь не найден", delete_after=300)
            return
        embed.add_field(name="Имя", value=cuser["name"])
        embed.add_field(name="Позиция", value=cuser["place"])
        embed.add_field(name="Кол-во побед", value=cuser["wins"])
        await ctx.author.send(embed=embed)

    @commands.command(name="user")
    async def user(self, ctx: commands.Context, name: str):
        await ctx.message.delete(delay=300)
        embed = discord.Embed()
        embed.colour = discord.Colour.red()
        embed.title = "Дискорд игрока"
        try:
            cuser = await get_user(name)
        except ServerCode404:
            await ctx.send("Извините, но такой пользователь не найден", delete_after=300)
            return
        embed.add_field(name="Имя", value=cuser["name"])
        if cuser.get("discord"):
            embed.add_field(name="Дискорд", value="<@!{}>".format(cuser["discord"]))
        else:
            embed.set_footer(text="Извините, но данный пользователь не привязал свой дискорд")
        await ctx.author.send(embed=embed)

    @commands.command(name="player")
    async def player(self, ctx: commands.Context, user: UUserConverter):
        await ctx.message.delete(delay=300)
        embed = discord.Embed()
        embed.colour = discord.Colour.dark_red()
        embed.title = "Инормация об игроке"
        try:
            cuser = await get_user(user.id)
        except ServerCode404:
            await ctx.send("Извините, но такой пользователь не найден", delete_after=300)
            return
        embed.add_field(name="Имя", value=cuser["name"])
        embed.add_field(name="Дискорд", value=user.mention)
        embed.add_field(name="Позиция", value=cuser["place"])
        embed.add_field(name="Кол-во игр", value=cuser["all"])
        embed.add_field(name="Кол-во побед", value=cuser["wins"])
        embed.add_field(name="Кол-во поражений", value=cuser["loose"])
        embed.add_field(name="Онлайн", value="Да" if cuser["status"] else "Нет")
        await ctx.author.send(embed=embed)

    @commands.command(name="friends")
    async def friends(self, ctx: commands.Context):
        await ctx.message.delete(delay=300)
        try:
            user = await get_user(ctx.author.id)
        except ServerCode404:
            await ctx.send("Извините, но вы не привязали дискорд в личном кабинете",
                           delete_after=300)
            return
        friends = await get_friends(user["name"])
        data = {"confirmed": {"title": "Друзья", "description": "",
                              "footer": "Извините, но у вас нет друзей"},
                "requested": {"title": "Ваши заявки в друзья", "description": "",
                              "footer": "У вас нет заявок в друзья"},
                "received": {"title": "Вас хотят добавить", "description": "",
                             "footer": "Вами никто не интересуется"}}
        for k, embed_data in friends.items():
            embed = discord.Embed(title=data[k]["title"], description=data[k]["description"])
            if not embed_data:
                embed.set_footer(text=data[k]["footer"])
            for friend in embed_data:
                embed.add_field(name=friend["name"] + (
                    " | <@!{}>".format(friend["discord"]) if friend.get("discord") else ""),
                                value="Онлайн" if friend["status"] else "Оффлайн")
            await ctx.author.send(embed=embed)

    @commands.command(name="add_friend")
    async def add_friend(self, ctx: commands.Context, user: typing.Union[UUserConverter, str]):
        await ctx.message.delete(delay=300)
        if isinstance(user, discord.User) and (user == ctx.author):
            return
        try:
            cuser = await get_user(ctx.author.id)
        except ServerCode404:
            await ctx.send("Вы не привязали аккаунт discord к профилю", delete_after=300)
            return
        if isinstance(user, discord.User):
            try:
                name = (await get_user(user.id))["name"]
            except ServerCode404:
                await ctx.send("Ваш друг не привязал аккаунт discord", delete_after=300)
                return
        elif isinstance(user, str):
            name = user
        async with aiohttp.ClientSession() as session:
            response = await session.post(settings["api"] + "/api/friends/add",
                                          data={"user-name": cuser["name"], "friend-name": name},
                                          auth=aiohttp.BasicAuth(settings["token"], "unused"))
            if response.status == 400:
                await ctx.send("Данный пользователь уже добавлен", delete_after=300)
            elif response.status == 404:
                await ctx.send("Данный пользователь не существует", delete_after=300)
            else:
                friend = await response.json()
                embed = discord.Embed(title="Друг" if friend["friends"] else "Не друг",
                                      description="Ура, вы теперь официальные друзья" if friend[
                                          "friends"] else "Заявка в друзья отправлена успешно")
                embed.add_field(name="Имя", value=cuser["name"])
                if friend.get("discord"):
                    embed.add_field(name="Дискорд", value="<@!{}>".format(friend["discord"]))
                embed.add_field(name="Онлайн", value="Да" if cuser["status"] else "Нет")
                embed.add_field(name="Сессия",
                                value=friend["session"]["name"] if friend["session"] and
                                                                   friend["session"]["status"] in [
                                                                       4, 5] else "Не в игре")
                await ctx.author.send(embed=embed)

    @commands.command(name="remove_friend")
    async def remove_friend(self, ctx: commands.Context, user: typing.Union[UUserConverter, str]):
        await ctx.message.delete(delay=300)
        if isinstance(user, discord.User) and (user == ctx.author):
            return
        try:
            cuser = (await get_user(ctx.author.id))["name"]
        except ServerCode404:
            await ctx.send("Вы не привязали аккаунт discord к профилю", delete_after=300)
            return
        if isinstance(user, discord.User):
            try:
                name = (await get_user(user.id))["name"]
            except ServerCode404:
                await ctx.send("Ваш друг не привязал аккаунт discord", delete_after=300)
                return
        elif isinstance(user, str):
            name = user
        async with aiohttp.ClientSession() as session:
            response = await session.post(settings["api"] + "/api/friends/remove",
                                          data={"user-name": cuser, "friend-name": name},
                                          auth=aiohttp.BasicAuth(settings["token"], "unused"))
            if response.status == 404 and (await response.text()) == "This user not friend":
                await ctx.send("Вы уже не друзья", delete_after=300)
            elif response.status == 404 and (await response.text()) == "User not exist":
                await ctx.send("Данный пользователь не существует", delete_after=300)
            else:
                embed = discord.Embed(title="Бывший друг",
                                      description="Ура, вы сбросили эти оковы с плеч")
                if isinstance(user, discord.User):
                    embed.add_field(name="Старый друг",
                                    value="{} | {}".format(user.name, user.mention))
                elif isinstance(user, str):
                    embed.add_field(name="Старый друг", value=user)
                await ctx.author.send(embed=embed)

    @commands.command(name="sessions")
    async def sessions(self, ctx: commands.Context, page: int = 1):
        await ctx.message.delete(delay=300)
        if page < 1:
            return
        async with aiohttp.ClientSession() as session:
            sessions = await (await session.get(settings["api"] + "/api/sessions")).json()
        if not sessions:
            await ctx.author.send("Сейчас на наших серверах нет активных сессий")
            return
        if not (page <= (len(sessions) + 9) // 10):
            await ctx.author.send("Такой страницы не существует")
            return
        embed = discord.Embed()
        embed.title = "Сессии №{}".format(page)
        embed.description = "Вам показаны сессии на {} странице из {}".format(page, (
                len(sessions) + 9) // 10)
        for session in sessions[(page - 1) * 10: page * 10]:
            users = ", ".join(
                [u["name"] for u in session["users"] if session["host"]["name"] != u["name"]])
            embed.add_field(
                name="{} {}/{}".format(session["name"], len(session["users"]), session["limit"]),
                value="```Хост: {}\nИгроки: {}\nСтатус: {}\nОписание: {}```".format(
                    session["host"]["name"],
                    users if users else "-",
                    "Игра идет" if session["status"] == 6 else "Лобби открыто",
                    session["desc"] if session["desc"] else "-"))
        await ctx.author.send(embed=embed)

    @top.error
    @link.error
    @place.error
    @user.error
    @player.error
    @friends.error
    @add_friend.error
    @remove_friend.error
    @sessions.error
    async def forbidden_handler(self, ctx, error):
        if isinstance(error.original, discord.Forbidden):
            await ctx.send("Извините, вы не открыли личные сообщения", delete_after=300)
        elif isinstance(error.original, ServerNotResponded):
            await ctx.send("Извините, но сервер в данный момент недоступен", delete_after=300)
        else:
            print(error.original)
            await ctx.send("Извините, у нас возникла непредвиденная ошибка", delete_after=300)


@bot.event
async def on_ready():
    global guild
    print("Starting")
    try:
        guild = bot.get_guild(settings["server_id"])
        if not guild:
            print("Сначала пригласите бота на сервер")
            await bot.logout()
            return
    except KeyError:
        print("Вы не указали server_id в settings.json")
        await bot.logout()
        return
    for channel in settings.get("channels", []):
        try:
            name = str_to_name(channel["name"])
        except KeyError:
            print("Вы не указали name канала в settings.json")
            await bot.logout()
            return
        test = discord.utils.get(guild.text_channels, name=name)
        if test:
            if channel.get("replace", True):
                await test.delete(reason="Replace channel")
            else:
                continue
        permissions = channel.get("permissions", []).copy()
        overwrites = {}
        for permission in permissions:
            try:
                role = guild.default_role if permission["role"] == "everyone" else guild.get_role(
                    permission["role"])
                if not role:
                    print("Вы указали неверный role(id) в settings.json в permissions")
                    await bot.logout()
                    return
            except KeyError:
                print("Вы не указали role(ее id) в settings.json в permissions")
                await bot.logout()
                return
            del permission["role"]
            overwrites[role] = discord.PermissionOverwrite(**permission)
        t_channel: discord.TextChannel = await guild.create_text_channel(name, overwrites=overwrites)

        for message in channel.get("messages", []):
            try:
                m_type = message["type"]
            except KeyError:
                print("Вы не указали type сообщения в settings.json")
                await bot.logout()
                return
            if m_type == "text":
                try:
                    await t_channel.send(message["text"])
                except KeyError:
                    print("Вы не указали text сообщения в settings.json")
                    await bot.logout()
                    return
            elif m_type == "embed":
                embed = discord.Embed(title=message.get("name", ""),
                                      description=message.get("value", ""))
                embed.colour = discord.Colour.blurple()
                for field in message.get("fields", []):
                    embed.add_field(name=field.get("name", ""), value=field.get("value", ""))
                await t_channel.send(embed=embed)
        if channel.get("webhook"):
            await t_channel.create_webhook(name=channel["webhook"], reason="Init")
    bot.loop.create_task(every_half_hour_update_top())
    print("End starting")


async def every_half_hour_update_top():
    while True:
        try:
            await update_top()
        except ServerNotResponded:
            print("update_top", "ServerNotResponded")
        except ChannelNotExist:
            print("update_top", "ChannelNotExist")
        except Exception as e:
            print("update_top", e)
        await asyncio.sleep(1800)


def main():
    bot.add_cog(RandomThings(bot))
    if not settings.get("api"):
        print("Вы не указали api в settings.json")
        return
    try:
        bot.run(settings["token"])
    except KeyError:
        print("Вы не указали токен в settings.json")
        return


if __name__ == "__main__":
    main()
