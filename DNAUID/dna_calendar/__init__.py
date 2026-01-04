from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from .draw_calendar_card import draw_calendar_img

sv_dna_calendar = SV("dna日历")


@sv_dna_calendar.on_fullmatch(("日历"), block=True)
async def send_dna_calendar_pic(bot: Bot, ev: Event):
    im = await draw_calendar_img(ev)
    return await bot.send(im)
