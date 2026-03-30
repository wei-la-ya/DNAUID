import json
import datetime

import aiohttp

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment


async def get_dna_code_info(bot: Bot, ev: Event):
    JSON_URL = "https://raw.gitcode.com/m0_69204072/dna/raw/main/dna_codes.json"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(JSON_URL) as resp:
                text = await resp.text()
                data = json.loads(text)

        tz = datetime.timezone(datetime.timedelta(hours=8))
        now = datetime.datetime.now(tz)

        valid_codes = []
        end_time_str = ""

        for item in data.get("data", []):
            ts = item["end_at"]
            end_time = datetime.datetime.fromtimestamp(ts, tz=tz)

            if end_time > now:
                valid_codes.append(item["code"])
                if not end_time_str:
                    end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        if not valid_codes:
            await bot.send("[DNA兑换码] 暂无可用兑换码")
            return

        node_list = [MessageSegment.text("[DNA兑换码]")]
        for code in valid_codes:
            node_list.append(MessageSegment.text(code))
        node_list.append(MessageSegment.text(f"有效期至：{end_time_str}"))

        forward_msg = MessageSegment.node(node_list)
        await bot.send(forward_msg)

    except Exception as e:
        logger.error(f"错误: {e}")
        await bot.send("[DNA兑换码] 获取失败")
