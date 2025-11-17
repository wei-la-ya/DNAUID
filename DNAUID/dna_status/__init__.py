from gsuid_core.status.plugin_status import register_status

from ..utils.database.models import DNASign, DNAUser
from ..utils.image import get_ICON
from ..utils.utils import get_yesterday_date


async def get_today_sign_num():
    datas = await DNASign.get_all_sign_data_by_date()
    return len(datas)


async def get_yesterday_sign_num():
    yesterday = get_yesterday_date()
    datas = await DNASign.get_all_sign_data_by_date(date=yesterday)
    return len(datas)


async def get_user_num():
    datas = await DNAUser.get_dna_all_user()
    return len(datas)


register_status(
    get_ICON(),
    "DNAUID",
    {
        "登录账户": get_user_num,
        "今日签到": get_today_sign_num,
        "昨日签到": get_yesterday_sign_num,
    },
)
