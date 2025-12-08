from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from .guide import get_guide
from ..utils.constants.constants import PATTERN

sv_dna_guide = SV("dna攻略")


@sv_dna_guide.on_regex(rf"^(?P<char_name>{PATTERN})攻略$", block=True)
async def send_role_guide_pic(bot: Bot, ev: Event):
    char_name = ev.regex_dict.get("char_name", "")
    await get_guide(bot, ev, char_name)
