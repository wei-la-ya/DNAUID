from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from .draw_role_card import draw_role_card
from ..utils.constants.constants import PATTERN

dna_role_detail_card = SV("dna角色详情卡片")


@dna_role_detail_card.on_regex(
    rf"^(?P<char_name>{PATTERN})(面板|信息|详情|面包|🍞)$",
    block=True,
)
async def send_role_detail_card(bot: Bot, ev: Event):
    char_name = ev.regex_dict.get("char_name", "")
    await draw_role_card(bot, ev, char_name)
