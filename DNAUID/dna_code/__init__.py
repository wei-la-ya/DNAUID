from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from .code import get_dna_code_info

sv_dna_code = SV("dna兑换码", priority=5)


@sv_dna_code.on_fullmatch(
    ("兑换码", "cdk", "CDK", "code"),
    block=True,
)
async def dna_code(bot: Bot, ev: Event):
    await get_dna_code_info(bot, ev)
