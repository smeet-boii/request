from redis.exceptions import RedisError
from redis.asyncio import Redis
import traceback
import aiofiles
from pyrogram.types import (
    ChatJoinRequest,
    ChatMemberUpdated,
    ChatPrivileges,
    Message,
)
from pyrogram.filters import channel, command, group, private, user
from pyrogram.errors import (
    ChannelPrivate,
    ChatAdminRequired,
    FloodWait,
    RPCError,
    UserAlreadyParticipant,
    UserChannelsTooMuch,
    FloodWait,
    InputUserDeactivated,
    UserIsBlocked,
    PeerIdInvalid
)
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram import Client, idle
from asyncio import sleep
from contextlib import suppress
from gc import collect
from logging import WARNING, getLogger

from os import remove
import time
import datetime
from sys import exit as exiter

from uvloop import install

install()

getLogger("pyrogram").setLevel(WARNING)
pbot = Client(
    "approver",
    20157264,
    "25c92d8a408af51fe25d6ad5b07968a5",
    bot_token="6033738522:AAEZsIfvw4e8oc_-BrwpCL8jpW5PUhtB1PI",
)
fetcher = Client(
    "fetcher",
    20157264,
    "25c92d8a408af51fe25d6ad5b07968a5",
    no_updates=True,
    session_string="AQFT7RAAAcoNAiksnvNWxVx9A_a97gLc2UwEGpDK5-hy6oqip8FTLQdNi44gmwr_s2vAjgomoWfhR9dLVXw_EWlZQprJmH2c5V_ANeP2G6UbPlyxKNASENYJPs-9eBdrB6kvKIcmeHH7rg6jsmsgv2-iJu65jYbrrWaupq8FrtiLHXuPcsrWt_7yYNwVov6LBXB-DdaMrXrJEsD5rqxmaQicg950ORZO0S90EfL4jn82qxvXk5zU_Jp26y1JjWoF1Prd9MZR--cNIrRe0bVyDQD1if-B-n6-3qXGxNa-_xLghSQ3KcTsLRN6kDHkWMx54WsSGg4zctY9K_6SC0sonc1OWPCkpgAAAAFT_GccAA",
)
ubotid, botid = 5704017692, 6033738522
OWNER = [1633375527, 2107284001, 5763778450]
REDIS = Redis.from_url(
    "redis://default:AE6MVJKDrCYBnFvSQ4pPXfY5ZACYib1x@redis-14396.c267.us-east-1-4.ec2.cloud.redislabs.com:14396",
    decode_responses=True,
)


async def approver(m: Message | ChatJoinRequest):
    try:
        await send_pm_notify(m)
        await pbot.approve_chat_join_request(m.chat.id, m.from_user.id)
        await REDIS.sadd("users", m.from_user.id)
    except FloodWait as fe:
        await sleep(fe.value + 0.5)
        await send_pm_notify(m)
        await pbot.approve_chat_join_request(m.chat.id, m.from_user.id)
        await REDIS.sadd("users", m.from_user.id)
    except Exception:
        pass


async def send_pm_notify(m: ChatJoinRequest):
    try:
        await pbot.send_message(
            m.from_user.id,
            "**Request Accepted! Use **/start **to get started!",
        )
    except FloodWait as ej:
        await sleep(ej.value + 0.5)
        await pbot.send_message(
            m.from_user.id,
             "**Request Accepted! Use **/start **to get started!",

        )
    except Exception as e:
        print(e)
        pass
    return


async def broadcaster(m: Message):
    if not m.reply_to_message:
        await m.reply_text("Reply to a well formatted message!")
        return
    aa = await m.reply_text("Doing ...!")
    done = 0
    failed = 0
    success = 0
    start_time = time.time()
    total_users = await REDIS.smembers("users")
    async with aiofiles.open('broadcast.txt', 'w') as broadcast_log_file:
        for x in total_users:
            sts, msg = await send_msg(int(x), m.reply_to_message)
            # print(sts, msg)
            if msg is not None:
                await broadcast_log_file.write(msg)
            if sts == 200:
                success += 1
            else:
                failed += 1
            if sts == 400:
                await REDIS.srem("users", x)
            done += 1
    completed_in = datetime.timedelta(seconds=int(time.time()-start_time))
    if failed == 0:
        await aa.reply_text(
            text=f"broadcast completed in `{completed_in}`\n\nTotal users {len(total_users)}.\nTotal done {done}, {success} success and {failed} failed.",
            quote=True
        )
    else:
        await m.reply_document(
            document='broadcast.txt',
            caption=f"broadcast completed in `{completed_in}`\n\nTotal users {len(total_users)}.\nTotal done {done}, {success} success and {failed} failed.",
            quote=True
        )
    
    await aiofiles.os.remove('broadcast.txt')


async def send_msg(user_id, message):
    try:
        await message.copy(user_id)
        await sleep(1)
        return 200, None
    except FloodWait as e:
        await sleep(e.x)
        return send_msg(user_id, message)
    except InputUserDeactivated:
        return 400, f"{user_id} : deactivated\n"
    except UserIsBlocked:
        return 400, f"{user_id} : blocked the bot\n"
    except PeerIdInvalid:
        return 400, f"{user_id} : user id invalid\n"
    except Exception as e:
        return 500, f"{user_id} : {traceback.format_exc()}\n"


async def acceptold(c: Client, m: Message | ChatMemberUpdated):
    data = m.text.split(maxsplit=1)[1:] if isinstance(m, Message) else []
    if m.chat.type != ChatType.PRIVATE:
        data.append(m.chat.id)
        aa = None
        if m.chat.type == ChatType.SUPERGROUP:
            await sleep(2)
    else:
        aa = await m.reply_text("Processing ...")
    if len(data) != 1:
        await edit_text(aa, "Provide a chat_id or username to process!")
        return
    try:
        try:
            chat = await c.get_chat(data[0])
        except FloodWait as fe:
            await sleep(fe.value + 0.5)
            chat = await c.get_chat(data[0])
        if chat.type == ChatType.PRIVATE:
            await edit_text(aa, "Private chats don't have join requests lol.")
            return
        await edit_text(aa, "Promoting ...!")
        with suppress(UserAlreadyParticipant):
            try:
                await fetcher.join_chat(chat.invite_link)
            except FloodWait as fe:
                await sleep(fe.value + 0.5)
                await fetcher.join_chat(chat.invite_link)
            except UserChannelsTooMuch:
                await edit_text(
                    aa,
                    "User account have too many joined chats currently contact owner!",
                )
            except TypeError:
                await edit_text(aa, "Something went wrong!")
                return
        try:
            botu = await chat.get_member(botid)
        except FloodWait as fe:
            await sleep(fe.value + 0.5)
            botu = await chat.get_member(botid)
        if botu.status != ChatMemberStatus.ADMINISTRATOR:
            await edit_text(aa, "I'm not admin there!")
            return
        if botu.privileges and not (
            botu.privileges.can_invite_users
            and botu.privileges.can_promote_members
            and botu.privileges.can_restrict_members
        ):
            await edit_text(
                aa,
                "I'm not admin there with wanted permissions that are: can_invite, can_restrict, can_promote!",
            )
            return
        if aa:
            try:
                fromu = await chat.get_member(m.from_user.id)
            except FloodWait as fe:
                await sleep(fe.value + 0.5)
                fromu = await chat.get_member(m.from_user.id)
            if fromu.privileges and not (
                fromu.privileges.can_restrict_members
                and fromu.privileges.can_promote_members
                and fromu.privileges.can_invite_users
            ):
                await edit_text(
                    aa,
                    "You are not admin there with wanted permissions that are: can_restrict, can_promote, can_invite!",
                )
                return
        try:
            await chat.promote_member(
                ubotid,
                privileges=ChatPrivileges(
                    can_manage_chat=True,
                    can_invite_users=True,
                    can_restrict_members=True,
                ),
            )
        except FloodWait as fe:
            await sleep(fe.value + 0.5)
            await chat.promote_member(
                ubotid,
                privileges=ChatPrivileges(
                    can_manage_chat=True,
                    can_invite_users=True,
                    can_restrict_members=True,
                ),
            )
        except (ValueError, RPCError) as e:
            await edit_text(aa, e.MESSAGE)
            return
        await edit_text(aa, "Now fetching users ...!")
        users = len(
            [
                x.user.id
                async for x in fetcher.get_chat_join_requests(chat.id)
                if x.pending
            ]
        )
        if users == 0:
            with suppress(Exception):
                await fetcher.leave_chat(chat.id)
            await edit_text(aa, "No pending join requests!")
            return
        await edit_text(aa, f"Processing {users} user's requests ...!")
        total = int(users / 50 if users > 50 else 50 / users)
        for sl in range(1, total):
            try:
                await fetcher.approve_all_chat_join_requests(chat.id)
                await edit_text(
                    aa,
                    f"Progress:\n{sl}/ {total} slots completed ( 50 members in each slot ) ...!",
                )
                await sleep(1)
            except Exception:
                continue
        with suppress(Exception):
            await fetcher.leave_chat(chat.id)
    except (RPCError, ChannelPrivate, ChatAdminRequired) as e:
        await edit_text(aa, e.MESSAGE)
        return
    await edit_text(aa, "Done!")
    return


@pbot.on_chat_join_request(channel | group)
async def autoapprove(c: pbot, m: ChatJoinRequest):
    collect()
    if not await REDIS.sismember("autoaccept", str(m.chat.id)):
        return
    c.loop.create_task(approver(m))
    return


@pbot.on_chat_member_updated(channel | group)
async def member_has_joined(c: pbot, m: ChatMemberUpdated):
    if (
        not m.new_chat_member
        or m.new_chat_member.status
        in (
            ChatMemberStatus.BANNED,
            ChatMemberStatus.LEFT,
            ChatMemberStatus.RESTRICTED,
        )
        or m.old_chat_member
    ):
        return
    if m.new_chat_member.user.id == botid:
        collect()
        await c.loop.create_task(acceptold(c, m))
    return


@pbot.on_message(command("total_user") & user(OWNER))
async def stats(_: pbot, m: Message):
    await m.reply_text(f"**Users:** {len(await REDIS.sunion('users'))}!")
    return


async def edit_text(m: Message | None, data: str):
    with suppress(Exception):
        if m:
            await m.edit_text(data)
    return


@pbot.on_message(command("start") & private)
async def start(_: pbot, m: Message):
    print(await pbot.get_chat(6176741647))
    await m.reply_text(
        """Hello, Welcome to Our Bot!

You can Use this bot to Automatically accept the Join Requests in your channels❤️

Follow steps:

Add this bot as ADMIN in your Channels.

◾ Send this Command to the bot:
/auto_accept {Channel's ID} true
To turn ON the Bot in that channel

◾ Send Comand:
/auto_accept {Channel's ID} false
To Stop the bot in that particular channel""",
    )
    if m.chat.type == ChatType.PRIVATE and m.from_user.id not in OWNER:
        await REDIS.sadd("users", m.from_user.id)
    return


@pbot.on_message(command("broadcast") & user(OWNER))
async def broadcast(c: pbot, m: Message):
    collect()
    c.loop.create_task(broadcaster(m))
    return


@pbot.on_message(command("accept_pending_request") & private & user(OWNER))
async def acceptcmder(c: Client, m: Message):
    collect()
    await c.loop.create_task(acceptold(c, m))
    return


@pbot.on_message(command("auto_accept"))
async def acceptoggle(c: Client, m: Message):
    collect()
    try:
        data, flag = m.text.split()[1], m.text.split()[2]
    except IndexError:
        return await m.reply_text("Provide a chat_id and True/False!")
    if flag.lower() not in ("true", "false"):
        return await m.reply_text("Provide a chat_id and True/False!")
    if flag.lower() == "true":
        if data in await REDIS.smembers("autoaccept"):
            return await m.reply_text("Already turned on!")
        await REDIS.sadd("autoaccept", data)
        await m.reply_text("Done turning on auto accept!")
    else:
        if data not in await REDIS.smembers("autoaccept"):
            return await m.reply_text("Already turned off!")
        await REDIS.srem("autoaccept", data)
        await m.reply_text("Done turning off auto accept!")


async def starter():
    with suppress(OSError):
        remove("unknown_errors.txt")
    try:
        await REDIS.ping()
        print("Your redis server is alive!")
    except RedisError:
        exiter("Your redis server is not alive, please check again!")
    await pbot.start()
    await fetcher.start()
    print("Started!")
    await idle()
    await pbot.stop(True)
    await fetcher.stop(True)
    await REDIS.close(True)
    with suppress(OSError):
        remove("unknown_errors.txt")
    print("Bye!")
    return


pbot.run(starter())
