import sqlite3
import json
import urllib.request
import urllib.parse
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.logger import logger

router = Router()
DB = "/opt/voicebot/bot.db"
B2S = "https://api.blog2social.com/rest/v1.0"
VK_NETWORK_ID = 17
VK_TYPE_GROUP = 2
VK_TYPE_PAGE = 1


def b2s_call(path, payload):
    r = urllib.request.Request(B2S + path, data=json.dumps(payload).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=30))


def service_token():
    return open("/opt/voicebot/keys/b2s_service.txt").read().strip()


def get_token(user_id):
    c = sqlite3.connect(DB)
    row = c.execute("SELECT b2s_token FROM users WHERE user_id=?", (user_id,)).fetchone()
    c.close()
    return row[0] if row and row[0] else None


def auth_link(st, tok, type_id):
    res = b2s_call("/network/add", {"service_token": st, "access_token": tok,
                                    "network_id": VK_NETWORK_ID,
                                    "network_type_id": type_id,
                                    "language": "ru"})
    return urllib.parse.unquote(res["auth_link"])


def vk_list(user_id):
    tok = get_token(user_id)
    res = b2s_call("/user/auth/list", {"service_token": service_token(), "access_token": tok})
    found = [x for x in res if x.get("network_id") == VK_NETWORK_ID]
    unique = []
    seen = set()
    for item in found:
        key = item.get("type_id")
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def save_network(user_id, network_id):
    c = sqlite3.connect(DB)
    c.execute("UPDATE users SET b2s_network_id=? WHERE user_id=?", (network_id, user_id))
    c.commit()
    c.close()


def nice_name(item):
    name = item.get("display_name") or "ВКонтакте"
    if len(name) > 40:
        name = name[:39] + "…"
    kind = "страница" if item.get("type") == "page" else "группа"
    return f"{name} ({kind})"


async def start_vk(message: Message, user_id: int) -> None:
    try:
        st = service_token()
        tok = get_token(user_id)
        if not tok:
            res = b2s_call("/user/auth", {"service_token": st})
            tok = res.get("access_token")
            c = sqlite3.connect(DB)
            c.execute("UPDATE users SET b2s_token=? WHERE user_id=?", (tok, user_id))
            c.commit()
            c.close()
            logger.info(f"B2S novyy polzovatel dlya {user_id}")
    except Exception as e:
        logger.error(f"B2S setvk FAILED: {e}")
        await message.answer("Не получилось начать подключение. Напиши в поддержку @Alex_protiv")
        return

    links = {}
    for name, type_id in (("group", VK_TYPE_GROUP), ("page", VK_TYPE_PAGE)):
        try:
            links[name] = auth_link(st, tok, type_id)
        except Exception as e:
            logger.error(f"B2S link {name} FAILED: {e}")

    if not links:
        logger.error(f"B2S setvk: obe ssylki ne poluchilis dlya {user_id}")
        await message.answer("Не получилось начать подключение. Напиши в поддержку @Alex_protiv")
        return

    rows = []
    if "group" in links:
        rows.append([InlineKeyboardButton(text="У меня группа", url=links["group"])])
    if "page" in links:
        rows.append([InlineKeyboardButton(text="У меня страница", url=links["page"])])
    rows.append([InlineKeyboardButton(text="Я подключил", callback_data="b2s_check")])

    await message.answer(
        "Подключаем ВКонтакте.\n\n"
        "В ВК два вида сообществ, и подключаются они по-разному:\n"
        "• в группе люди называются участниками\n"
        "• на странице — подписчиками\n\n"
        "Не помнишь, что у тебя — не страшно. Открой обе кнопки по очереди, "
        "в одной из них твоё сообщество найдётся.\n\n"
        "1. Нажми кнопку и найди своё сообщество в списке\n"
        "2. Проверь название и нажми «Разрешить»\n"
        "3. Вернись сюда и нажми «Я подключил»\n\n"
        "⚠️ Ссылку открывай в обычном браузере, где ты уже вошёл в ВК. "
        "Если она откроется прямо в Телеграме — зажми её и выбери «Открыть в браузере».\n\n"
        "Ссылка живёт несколько минут. Не успел — набери /setvk заново.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.message(Command("setvk"))
async def handle_setvk(message: Message) -> None:
    await start_vk(message, message.from_user.id)


@router.callback_query(F.data == "go_setvk")
async def handle_setvk_button(callback: CallbackQuery) -> None:
    await start_vk(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "b2s_check")
async def handle_check(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    await callback.answer()
    try:
        found = vk_list(user_id)
    except Exception as e:
        logger.error(f"B2S check FAILED: {e}")
        await callback.message.answer("Не смог проверить. Попробуй ещё раз или напиши @Alex_protiv")
        return

    if not found:
        await callback.message.answer(
            "Пока не вижу подключения.\n\n"
            "Чаще всего дело в том, что открыта не та кнопка. "
            "Загляни в своё сообщество и посмотри, как называется список людей:\n"
            "• участники — это группа\n"
            "• подписчики — это страница\n\n"
            "Потом набери /setvk и открой ту кнопку, которая подходит.\n\n"
            "Вторая причина — браузер вошёл в другой аккаунт ВК. "
            "Открой vk.com и проверь, тот ли это аккаунт, где живёт твоё сообщество.\n\n"
            "Не получается — напиши @Alex_protiv, разберёмся вместе")
        return

    if len(found) == 1:
        net = found[0]
        save_network(user_id, net["client_user_network_id"])
        logger.info(f"B2S podklyuchen {user_id} -> {net['client_user_network_id']}")
        await callback.message.answer(
            f"Готово! Подключено сообщество: {nice_name(net)}\n\n"
            "Теперь твои посты будут уходить и в ВК — вместе с картинкой.\n\n"
            "Отключить: /vkoff")
        return

    rows = [[InlineKeyboardButton(text=nice_name(x),
                                  callback_data=f"b2s_pick:{x['client_user_network_id']}")]
            for x in found]
    logger.info(f"B2S vybor iz {len(found)} dlya {user_id}")
    await callback.message.answer(
        "Нашёл несколько подключённых сообществ.\n\n"
        "Выбери то, куда должны уходить посты:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("b2s_pick:"))
async def handle_pick(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    await callback.answer()
    picked = callback.data.split(":", 1)[1]
    try:
        found = vk_list(user_id)
        net = next((x for x in found if str(x["client_user_network_id"]) == picked), None)
        if not net:
            await callback.message.answer(
                "Это сообщество больше не подключено. Набери /setvk и попробуй заново.")
            return
        save_network(user_id, net["client_user_network_id"])
        logger.info(f"B2S vybran {user_id} -> {net['client_user_network_id']}")
        await callback.message.answer(
            f"Готово! Подключено сообщество: {nice_name(net)}\n\n"
            "Теперь твои посты будут уходить и в ВК — вместе с картинкой.\n\n"
            "Выбрал не то — набери /setvk и выбери заново.\n"
            "Отключить: /vkoff")
    except Exception as e:
        logger.error(f"B2S pick FAILED: {e}")
        await callback.message.answer("Не смог сохранить выбор. Попробуй ещё раз или напиши @Alex_protiv")


@router.message(Command("vkoff"))
async def handle_vkoff(message: Message) -> None:
    c = sqlite3.connect(DB)
    c.execute("UPDATE users SET vk_group_id=NULL, vk_token=NULL, b2s_network_id=NULL WHERE user_id=?",
              (message.from_user.id,))
    c.commit()
    c.close()
    await message.answer("ВКонтакте отключён. Посты будут уходить только в Telegram.\n\n"
                         "Подключить снова: /setvk")
