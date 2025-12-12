import asyncio
import datetime

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
import aiohttp

async def get_cdk_info(bot: Bot, ev: Event):
    url = "https://www.gamekee.com/v1/game/cdk/queryByServerIdPageList?limit=10&page_no=1&page_total=1&total=0&server_id=110&state=2&nick_name="
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
        "Referer": "https://www.gamekee.com/dna/redemptionCode/110",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Game-Alias": "dna",
        "Device-Num": "1",
        "Lang": "zh-cn",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()  # 检查请求是否成功
                
                data = await response.json()
        
        if data.get("code") == 0:
            cdks = data.get("data", [])
            
            if cdks:
                cdk_groups = {}
                for cdk in cdks:
                    end_at = cdk.get("end_at")
                    if end_at not in cdk_groups:
                        cdk_groups[end_at] = []
                    cdk_groups[end_at].append(cdk)
                
                valid_cdk_groups = {}
                current_time = datetime.datetime.now()
                for end_at, group_cdks in cdk_groups.items():
                    end_time = datetime.datetime.fromtimestamp(end_at)
                    if end_time > current_time:
                        valid_cdk_groups[end_at] = group_cdks
                
                if not valid_cdk_groups:
                    await bot.send("[DNA兑换码] 暂无兑换码")
                else:
                    for end_at, group_cdks in valid_cdk_groups.items():
                        end_time = datetime.datetime.fromtimestamp(end_at)
                        end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
                        
                        await bot.send(f"[DNA兑换码] 过期时间: {end_time_str}")
                        
                        for cdk in group_cdks:
                            code = cdk.get("code")
                            await bot.send(f"{code}")
            else:
                await bot.send("[DNA兑换码] 暂无兑换码")
        else:
            await bot.send(f"[DNA兑换码] 请求失败: {data.get('msg')}")
            
    except aiohttp.ClientError as e:
        logger.error(f"[DNA兑换码] 网络请求错误: {e}")
        await bot.send(f"[DNA兑换码] 网络请求错误: {e}")
    except ValueError as e:
        logger.error(f"[DNA兑换码] JSON解析错误: {e}")
        await bot.send(f"[DNA兑换码] JSON解析错误: {e}")