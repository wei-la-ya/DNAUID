from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from .draw_role_info_card import draw_role_info_card

dna_role = SV("dna查询卡片")


@dna_role.on_fullmatch(("查询", "卡片", "角色", "信息"))
async def send_role_info_card(bot: Bot, ev: Event):
    await draw_role_info_card(bot, ev)
