import re

from gsuid_core.aps import scheduler
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV

from ..utils import TZ
from ..utils.api.mh_map import get_mh_list
from .draw_mh import draw_mh
from .subscribe_mh import get_mh_subscribe, send_mh_notify, subscribe_mh, set_mh_push_time_range
from ..utils.msgs.notify import send_dna_notify

sv_mh = SV("dna密函")
sv_mh_list = SV("dna密函列表")
sv_mh_subscribe = SV("dna密函订阅")
sv_mh_help = SV("dna密函帮助")

RE_MH_LIST = "|".join(get_mh_list()) + "|全部"
RE_MH_TYPE_LIST = "|".join(["角色", "武器", "魔之楔"])


@sv_mh.on_fullmatch("密函", block=True)
async def send_mh(bot: Bot, ev: Event):
    return await draw_mh(bot, ev)


@sv_mh_list.on_fullmatch("密函列表", block=True)
async def send_mh_list(bot: Bot, ev: Event):
    return await bot.send("\n".join(get_mh_list()))


@sv_mh_subscribe.on_regex(rf"^(订阅|取消订阅)({RE_MH_TYPE_LIST})?({RE_MH_LIST})密函$")
async def dna_mh_subscribe(bot: Bot, ev: Event):
    if ev.bot_id != "onebot":
        logger.warning(f"非onebot禁止订阅密函【{ev.bot_id}】")
        return

    match = re.search(
        rf"(订阅|取消订阅)(?P<mh_type>{RE_MH_TYPE_LIST})?(?P<mh_name>{RE_MH_LIST})密函$",
        ev.raw_text,
    )
    if not match:
        return
    ev.regex_dict = match.groupdict()
    mh_type = ev.regex_dict.get("mh_type")
    mh_name = ev.regex_dict.get("mh_name")
    if not mh_name:
        return

    await subscribe_mh(bot, ev, mh_name, mh_type)


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


@sv_mh_subscribe.on_regex(r"^订阅密函时间(\d{1,2}):(\d{1,2})$")
async def dna_mh_set_push_time(bot: Bot, ev: Event):
    """设置密函推送时间段命令处理器"""
    if ev.bot_id != "onebot":
        logger.warning(f"非onebot禁止设置密函推送时间段【{ev.bot_id}】")
        return

    # 提取时间段
    match = re.search(r"订阅密函时间(\d{1,2}):(\d{1,2})", ev.raw_text)
    if not match:
        await send_dna_notify(bot, ev, "设置推送时间段格式错误，请使用格式: 订阅密函时间17:22")
        return

    start_hour, end_hour = match.groups()
    start_hour = int(start_hour)
    end_hour = int(end_hour)

    # 验证时间格式
    if start_hour > 23 or end_hour > 23:
        await send_dna_notify(bot, ev, "时间格式错误，请确保小时在0-23之间")
        return

    if start_hour >= end_hour:
        await send_dna_notify(bot, ev, "开始时间必须早于结束时间")
        return

    # 构建时间段格式 HH:MM-HH:MM，按照用户要求，使用用户输入的时间
    # 注意：用户输入的是 17:22 格式，表示 17:00-22:00
    time_range = f"{start_hour:02d}:00-{end_hour:02d}:00"
    
    await set_mh_push_time_range(bot, ev, time_range)


# 每小时5秒执行一次密函推送
@scheduler.scheduled_job("cron", hour="*", minute="0", second="5", timezone=TZ)
async def dna_push_mh_notify():
    await send_mh_notify()


# @sv_mh_subscribe.on_fullmatch("密函测试", block=True)
# async def send_mh_test(bot: Bot, ev: Event):
#     await send_mh_notify()
