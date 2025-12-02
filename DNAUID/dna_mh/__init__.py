from gsuid_core.aps import scheduler
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV

from ..dna_config.dna_config import DNAConfig
from ..utils import TZ
from ..utils.api.mh_map import get_mh_list
from ..utils.msgs.notify import send_dna_notify
from .draw_mh import draw_mh
from .push_mh import send_mh_notify
from .subscribe_mh import (
    get_mh_subscribe,
    subscribe_mh,
    subscribe_mh_pic,
    subscribe_mh_time,
)

sv_mh = SV("dna密函")
sv_mh_list = SV("dna密函列表")
sv_mh_subscribe = SV("dna密函订阅")
sv_mh_subscribe_cycle = SV("dna密函订阅周期")
sv_mh_pic_subscribe = SV("dna密函图片订阅", area="GROUP", pm=3)
sv_mh_test = SV("dna密函测试", pm=0)

RE_MH_LIST = "|".join(get_mh_list()) + "|全部"
RE_MH_TYPE_LIST = "|".join(["角色", "武器", "魔之楔"])

MHPUSH_TIME = DNAConfig.get_config("MHPushSubscribe").data
try:
    minute, second = MHPUSH_TIME.split(":")
    int_minute = int(minute)
    int_second = int(second)
    if int_minute < 0 or int_minute > 59 or int_second < 0 or int_second > 59:
        minute = "0"
        second = "5"
except ValueError:
    minute = "0"
    second = "5"


@sv_mh.on_fullmatch(("密函", "委托密函", "mh"), block=True)
async def send_mh(bot: Bot, ev: Event):
    return await draw_mh(bot, ev)


@sv_mh_list.on_fullmatch("密函列表", block=True)
async def send_mh_list(bot: Bot, ev: Event):
    return await bot.send("\n".join(get_mh_list()))


@sv_mh_subscribe.on_regex(
    rf"^(订阅|取消订阅)(?P<mh_type>{RE_MH_TYPE_LIST})?(?P<mh_name>{RE_MH_LIST})密函$"
)
async def dna_mh_subscribe(bot: Bot, ev: Event):
    if ev.bot_id != "onebot":
        logger.warning(f"非onebot禁止订阅密函【{ev.bot_id}】")
        return

    mh_type = ev.regex_dict.get("mh_type")
    mh_name = ev.regex_dict.get("mh_name")
    if not mh_name:
        return

    await subscribe_mh(bot, ev, mh_name, mh_type)


@sv_mh_subscribe_cycle.on_regex(r"^订阅密函(时间|周期)(\d{1,2}):(\d{1,2})$")
async def dna_mh_push_time(bot: Bot, ev: Event):
    if ev.bot_id != "onebot":
        logger.warning(f"非onebot禁止设置密函推送时间段【{ev.bot_id}】")
        return

    from ..dna_config.prefix import DNA_PREFIX

    msg = [
        "设置推送时间段格式错误，请使用以下格式",
        f"例如开始时间:17点, 结束时间:23点, 命令: {DNA_PREFIX}订阅密函时间17:23",
    ]
    msg = "\n".join(msg)

    _, start_hour, end_hour = ev.regex_group
    start_hour = int(start_hour)
    end_hour = int(end_hour)

    if (
        (start_hour < 0 or start_hour > 23)
        or (end_hour < 0 or end_hour > 23)
        or (start_hour > end_hour)
    ):
        await send_dna_notify(bot, ev, msg)
        return

    await subscribe_mh_time(bot, ev, ev.user_id, start_hour, end_hour)


@sv_mh_pic_subscribe.on_fullmatch(
    (
        "订阅密函图片",
        "取消订阅密函图片",
    ),
    block=True,
)
async def sub_mh_pic_subscribe(bot: Bot, ev: Event):
    if ev.bot_id != "onebot":
        logger.warning(f"非onebot禁止订阅密函【{ev.bot_id}】")
        return

    await subscribe_mh_pic(bot, ev)


@sv_mh_subscribe.on_fullmatch(
    (
        "密函订阅",
        "我的密函",
        "我的密函订阅",
    ),
    block=True,
)
async def send_mh_subscribe(bot: Bot, ev: Event):
    if ev.bot_id != "onebot":
        logger.warning(f"非onebot禁止获取密函订阅【{ev.bot_id}】")
        return

    await get_mh_subscribe(bot, ev)


@scheduler.scheduled_job("cron", hour="*", minute=minute, second=second, timezone=TZ)
async def dna_push_mh_notify():
    await send_mh_notify()


@sv_mh_test.on_fullmatch("密函测试", block=True)
async def send_mh_test(bot: Bot, ev: Event):
    await send_mh_notify()
