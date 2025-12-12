from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.sv import SV
from .cdk import get_cdk_info

sv_dna_cdk = SV("dna兑换码", priority=5)


@sv_dna_cdk.on_fullmatch(
    (
        "兑换码",
        "cdk",
        "CDK",
        "code"
    ),
    block=True,
)
async def dna_cdk(bot: Bot, ev: Event):
    await get_cdk_info(bot, ev)