import random
import asyncio
from typing import List, Literal
from datetime import timedelta
from collections import defaultdict

from gsuid_core.logger import logger
from gsuid_core.models import Message
from gsuid_core.segment import MessageSegment
from gsuid_core.subscribe import gs_subscribe
from gsuid_core.utils.database.models import Subscribe

from ..utils import get_datetime
from .draw_mh import draw_mh_card
from .cache_mh import get_mh_result
from .subscribe_mh import str2list, subscribe_mh_key
from ..utils.api.model import DNARoleForToolInstanceInfo
from ..utils.api.mh_map import get_mh_type_name
from ..dna_config.dna_config import DNAConfig
from ..utils.constants.boardcast import BoardcastTypeEnum


async def send_mh_notify():
    if not DNAConfig.get_config("MHSubscribe").data:
        return

    now = get_datetime()
    next_refresh = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    remaining_seconds = int((next_refresh - now).total_seconds())
    mh_result = await get_mh_result(int(next_refresh.timestamp()), is_force=True)
    if not mh_result:
        logger.warning("未找到有效的密函数据")
        return

    await push_text_notify(mh_result)
    await push_pic_notify(mh_result, remaining_seconds)


async def push_text_notify(mh_result: List[DNARoleForToolInstanceInfo]):
    if not mh_result:
        return

    subscribe_data = await gs_subscribe.get_subscribe(BoardcastTypeEnum.MH_SUBSCRIBE)
    if not subscribe_data:
        return

    # {"拆解": ["role", "weapon"], "角色:拆解": ["role"], "武器:拆解": ["weapon"]}
    mh_re_datas: defaultdict[str, list[Literal["role", "weapon", "mzx"]]] = defaultdict(list)
    for ins in mh_result:
        if not ins.mh_type:
            continue

        mh_type_name = get_mh_type_name(ins.mh_type)

        for m in ins.instances:
            mh_name = m.name.split("/")[0]
            mh_re_datas[mh_name].append(ins.mh_type)
            mh_re_datas[subscribe_mh_key(mh_name, mh_type_name)].append(ins.mh_type)
    # set("拆解", "勘探", "追缉", "角色:拆解", "武器:勘探", "魔之楔:勘探")
    mh_name_set = set(mh_re_datas.keys())

    async def private_push(subscribe: Subscribe, valid_mh_list: list[str]):
        if not valid_mh_list:
            return

        push_msg = []
        for key in valid_mh_list:
            mh_type_list = mh_re_datas[key]
            for mh_type in mh_type_list:
                mh_type_name = get_mh_type_name(mh_type)
                if ":" in key:
                    key = key.split(":")[1]
                push_msg.append(f"{mh_type_name} : {key}")

        if push_msg:
            push_msg.insert(0, "当前订阅密函已刷新:")
            await subscribe.send("\n".join(push_msg))
            await asyncio.sleep(0.5 + random.randint(1, 3))

    # 群聊数据
    groupid2sub = {}
    # {group_id: {"mh_type_name: mh_name": [@user_id]}}
    groupid2push_msg: defaultdict[str, defaultdict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    async def group_push(subscribe: Subscribe, valid_mh_list: list[str]):
        if not valid_mh_list:
            return
        if not subscribe.group_id:
            return
        for key in valid_mh_list:
            mh_type_list = mh_re_datas[key]
            for mh_type in mh_type_list:
                mh_type_name = get_mh_type_name(mh_type)
                if ":" in key:
                    key = key.split(":")[1]
                groupid2push_msg[subscribe.group_id][f"{mh_type_name} : {key}"].append(subscribe.user_id)

        if subscribe.group_id not in groupid2sub:
            groupid2sub[subscribe.group_id] = subscribe

    datetime_now = get_datetime()
    for subscribe in subscribe_data:
        if not subscribe.extra_message:
            continue

        if subscribe.extra_data:
            start_time, end_time = subscribe.extra_data.split(":")
            if datetime_now.hour < int(start_time) or datetime_now.hour > int(end_time):
                continue

        my_mh_list = str2list(subscribe.extra_message)
        valid_mh_list = []
        for i in mh_name_set:
            if i in my_mh_list:
                valid_mh_list.append(i)

        if "private" in DNAConfig.get_config("MHSubscribe").data and subscribe.user_type == "direct":
            await private_push(subscribe, valid_mh_list)
        elif (
            "group" in DNAConfig.get_config("MHSubscribe").data
            and subscribe.user_type == "group"
            and subscribe.group_id
        ):
            await group_push(subscribe, valid_mh_list)

    for group_id, _sub in groupid2sub.items():
        _sub: Subscribe
        push_msg = groupid2push_msg[group_id]
        if not push_msg:
            continue

        build_push_msg: List[Message] = [
            MessageSegment.text("当前订阅密函已刷新"),
            MessageSegment.text("\n"),
        ]

        for key, user_list in push_msg.items():
            build_push_msg.append(MessageSegment.text(f"{key}"))
            build_push_msg.append(MessageSegment.text("\n"))
            for user_id in user_list:
                build_push_msg.append(MessageSegment.at(user_id))
            build_push_msg.append(MessageSegment.text("\n"))

        await _sub.send(build_push_msg)
        await asyncio.sleep(0.5 + random.randint(1, 3))


async def push_pic_notify(mh_result: List[DNARoleForToolInstanceInfo], remaining_seconds: int):
    if not mh_result:
        return

    subscribe_data = await gs_subscribe.get_subscribe(BoardcastTypeEnum.MH_PIC_SUBSCRIBE)
    if not subscribe_data:
        return

    card = await draw_mh_card(mh_result, remaining_seconds)

    for subscribe in subscribe_data:
        await subscribe.send(card)
        await asyncio.sleep(random.uniform(1, 3))
