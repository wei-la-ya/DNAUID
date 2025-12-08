from typing import Optional
from pathlib import Path

from PIL import Image, ImageDraw

from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img

from ..utils import dna_api
from ..utils.image import (
    COLOR_WHITE,
    COLOR_SALMON,
    COLOR_GOLDENROD,
    COLOR_FIRE_BRICK,
    get_div,
    add_footer,
    get_dna_bg,
    get_mod_img,
    get_attr_img,
    get_grade_img,
    get_paint_img,
    get_skill_img,
    get_smooth_drawer,
    get_avatar_title_img,
)
from ..utils.api.model import (
    RoleInsForTool,
    DNARoleDetailRes,
    DNARoleForToolRes,
)
from ..utils.msgs.notify import (
    dna_not_found,
    dna_uid_invalid,
    dna_not_unlocked,
    dna_token_invalid,
)
from ..utils.name_convert import alias_to_char_name, char_name_to_char_id
from ..utils.database.models import DNABind
from ..utils.fonts.dna_fonts import (
    dna_font_18,
    dna_font_24,
    dna_font_26,
    dna_font_30,
)

TEXT_PATH = Path(__file__).parent / "texture2d"
prop_info_bar1 = Image.open(TEXT_PATH / "prop_info_bar1.png")
prop_info_bar2 = Image.open(TEXT_PATH / "prop_info_bar2.png")
global_skill_bg = Image.open(TEXT_PATH / "skill_bg.png")
grade_lock_img = Image.open(TEXT_PATH / "grade_0.png")
grade_unlock_img = Image.open(TEXT_PATH / "grade_1.png")

attr_list = [
    ("atk", "攻击", "icon1.png"),
    ("maxHp", "生命", "icon10.png"),
    ("maxES", "护盾", "icon11.png"),
    ("defense", "防御", "icon9.png"),
    ("maxSp", "最大神志", "icon8.png"),
    ("skillIntensity", "技能威力", "icon7.png"),
    ("skillRange", "技能范围", "icon6.png"),
    ("skillSustain", "技能耐久", "icon5.png"),
    ("skillEfficiency", "技能效益", "icon4.png"),
    ("strongValue", "昂扬", "icon3.png"),
    ("enmityValue", "背水", "icon2.png"),
]


async def draw_role_card(bot: Bot, ev: Event, char_name: str):
    uid = await DNABind.get_uid_by_game(ev.user_id, ev.bot_id)
    if not uid:
        await dna_uid_invalid(bot, ev)
        return

    dna_user = await dna_api.get_dna_user(uid, ev.user_id, ev.bot_id)
    if not dna_user:
        await dna_token_invalid(bot, ev)
        return

    real_char_name = alias_to_char_name(char_name)
    if not real_char_name:
        await dna_not_found(bot, ev, f"角色别名【{char_name}】")
        return

    char_id = char_name_to_char_id(real_char_name)
    if not char_id:
        await dna_not_found(bot, ev, f"角色【{char_name}】的CharId")
        return
    char_name = real_char_name

    default_role = await dna_api.get_default_role_for_tool(dna_user.cookie, dna_user.dev_code)
    if not default_role.is_success:
        await dna_not_found(bot, ev, "角色列表信息")
        return

    default_role = DNARoleForToolRes.model_validate(default_role.data)
    role_show = default_role.roleInfo.roleShow

    role_char_simple: Optional[RoleInsForTool] = next(
        (i for i in role_show.roleChars if str(i.charId) == char_id), None
    )
    if not role_char_simple:
        await dna_not_found(bot, ev, f"展柜角色【{char_name}】")
        return

    if not role_char_simple.unLocked or not role_char_simple.charEid:
        await dna_not_unlocked(bot, ev, f"当前展柜角色【{char_name}】")
        return

    role_detail = await dna_api.get_role_detail(dna_user.cookie, char_id, role_char_simple.charEid, dna_user.dev_code)
    if not role_detail.is_success:
        await dna_not_found(bot, ev, f"角色【{char_name}】详情")
        return

    role_detail = DNARoleDetailRes.model_validate(role_detail.data)
    role_detail = role_detail.charDetail

    card = get_dna_bg(1000, 2000, "bg2")

    # paint
    paint_img = await get_paint_img(char_id, role_detail.paint)
    paint_img = paint_img.resize((int(1320 * 0.8), int(1320 * 0.8)))
    card.alpha_composite(paint_img, (-280, -100))

    # 个人信息
    info_bg = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
    info_bg_draw = ImageDraw.Draw(info_bg)
    # 名字
    point = Image.open(TEXT_PATH / "point.png")
    info_bg.alpha_composite(point, (10, 10))
    info_bg_draw.text((50, 25), char_name, COLOR_WHITE, dna_font_30, "lm")
    # 属性
    attr_img = await get_attr_img(char_id, role_detail.elementIcon)
    attr_img = attr_img.resize((attr_img.width // 2, attr_img.height // 2))
    info_bg.alpha_composite(attr_img, (10, 40))
    # 命座
    grade_img = get_grade_img(role_detail.gradeLevel)
    ellipse = Image.new("RGBA", (34, 35))
    get_smooth_drawer().rounded_rectangle((0, 0, 34, 35), fill=COLOR_FIRE_BRICK, radius=7, target=ellipse)
    ellipse.alpha_composite(grade_img, (0, 5))
    info_bg.alpha_composite(ellipse, (50, 60))
    # 等级
    ellipse = Image.new("RGBA", (80, 35))
    ellipse_draw = ImageDraw.Draw(ellipse)
    get_smooth_drawer().rounded_rectangle((0, 0, 80, 35), fill=COLOR_FIRE_BRICK, radius=7, target=ellipse)
    ellipse_draw.text((40, 17), f"Lv.{role_detail.level}", COLOR_WHITE, dna_font_26, "mm")
    info_bg.alpha_composite(ellipse, (100, 60))

    card.alpha_composite(info_bg, (550, 80))

    # 命座解锁
    grade_unlock_bg = Image.new("RGBA", (1000, 130), (0, 0, 0, 0))
    for i in range(1, 7):
        grade_bg = grade_lock_img.copy() if i > role_detail.gradeLevel else grade_unlock_img.copy()
        grade_img = get_grade_img(i)
        grade_img = grade_img.resize((int(grade_img.width * 1.8), int(grade_img.height * 1.8)))
        grade_bg.alpha_composite(grade_img, (33, 37))
        grade_unlock_bg.alpha_composite(grade_bg, (100 + (i - 1) * 150, 0))

    grade_unlock_bg = grade_unlock_bg.resize((int(1000 * 0.5), int(130 * 0.5)))
    card.alpha_composite(grade_unlock_bg, (0, 750))

    # 属性
    attr_bg = Image.new("RGBA", (400, 583), (0, 0, 0, 128))
    for index, attrs in enumerate(attr_list):
        prop_info = prop_info_bar1.copy() if index % 2 == 0 else prop_info_bar2.copy()
        prop_info_draw = ImageDraw.Draw(prop_info)
        attr_value = f"{getattr(role_detail.attribute, attrs[0]) or ''}"

        icon = Image.open(TEXT_PATH / f"icons/{attrs[2]}")
        # icon
        prop_info.alpha_composite(icon, (0, 0))
        # 属性名
        prop_info_draw.text(
            (50, 25),
            attrs[1],
            COLOR_WHITE,
            font=dna_font_26,
            anchor="lm",
        )
        # 属性值
        prop_info_draw.text(
            (370, 25),
            (attr_value if "%" in attr_value or not attr_value.isdigit() else f"{int(attr_value):,}"),
            COLOR_WHITE,
            font=dna_font_26,
            anchor="rm",
        )
        attr_bg.alpha_composite(prop_info, (0, index * 53))

    card.alpha_composite(attr_bg, (550, 200))

    div = get_div()
    card.alpha_composite(div, (0, 850))

    # 技能
    for index, skill in enumerate(role_detail.skills):
        skill_bg = global_skill_bg.copy()
        skill_bg_draw = ImageDraw.Draw(skill_bg)

        skill_img = await get_skill_img(char_id, skill.skillName, skill.icon)
        skill_img = skill_img.resize((100, 100))
        skill_bg.alpha_composite(skill_img, (20, 30))

        # 技能名字
        if len(skill.skillName) <= 5:
            skill_bg_draw.text((120, 55), skill.skillName, COLOR_GOLDENROD, dna_font_24, "lm")
        else:
            skill_bg_draw.text(
                (120, 55),
                skill.skillName,
                COLOR_GOLDENROD,
                dna_font_18,
                "lm",
            )

        get_smooth_drawer().rounded_rectangle(
            (120, 80, 200, 110),
            10,
            COLOR_SALMON,
            target=skill_bg,
        )

        skill_bg_draw.text((160, 94), f"Lv.{skill.level}", COLOR_WHITE, dna_font_26, "mm")

        card.alpha_composite(skill_bg, (50 + index * 300, 920))

    div = get_div()
    card.alpha_composite(div, (0, 1100))

    # mod
    all_mod_bg = Image.new("RGBA", (1000, 500), (0, 0, 0, 0))
    # 左4
    left_list = role_detail.modes[:4]
    for index, mod in enumerate(left_list):
        quality = mod.quality or 1
        mod_bg = Image.open(TEXT_PATH / f"mod/mod_left_{quality}.png")
        mod_bg_draw = ImageDraw.Draw(mod_bg)

        if mod.id != -1 and mod.name:
            mod_img = await get_mod_img(mod.id, mod.icon)
            mod_img = mod_img.resize((180, 180))
            mod_bg.alpha_composite(mod_img, (35, 15))
            mod_bg_draw.text((115, 180), mod.name, COLOR_WHITE, dna_font_26, "mm")

        # 2行2列，先左右，再上下
        all_mod_bg.alpha_composite(mod_bg, (30 + (index % 2) * 180, (index // 2) * 250))

    # 右4
    right_list = role_detail.modes[4:8]
    for index, mod in enumerate(right_list):
        quality = mod.quality or 1
        mod_bg = Image.open(TEXT_PATH / f"mod/mod_right_{quality}.png")
        mod_bg_draw = ImageDraw.Draw(mod_bg)

        if mod.id != -1 and mod.name:
            mod_img = await get_mod_img(mod.id, mod.icon)
            mod_img = mod_img.resize((180, 180))
            mod_bg.alpha_composite(mod_img, (35, 15))
            mod_bg_draw.text((140, 180), mod.name, COLOR_WHITE, dna_font_26, "mm")

        # 2行2列，先左右，再上下
        all_mod_bg.alpha_composite(mod_bg, (530 + (index % 2) * 180, (index // 2) * 250))

    # 中1
    center_list = role_detail.modes[-1]
    quality = center_list.quality or 1
    mod_bg = Image.open(TEXT_PATH / f"mod/mod_center_{quality}.png")
    mod_bg_draw = ImageDraw.Draw(mod_bg)
    if center_list.id != -1 and center_list.name:
        mod_img = await get_mod_img(center_list.id, center_list.icon)
        mod_img = mod_img.resize((150, 150))
        mod_bg.alpha_composite(mod_img, (5, 5))
        mod_bg_draw.text((80, 170), center_list.name, COLOR_WHITE, dna_font_26, "mm")
    all_mod_bg.alpha_composite(mod_bg, (415, 100))

    card.alpha_composite(all_mod_bg, (0, 1200))

    # 头像等
    avatar_title = await get_avatar_title_img(
        ev,
        role_show.roleId,
        role_show.roleName,
        user_level=role_show.level,
        other_info=[(i.paramKey, i.paramValue) for i in role_show.params if i.paramKey in ("总活跃天数", "成就达成")],
    )
    avatar_title = avatar_title.resize((1000, 1000 * avatar_title.height // avatar_title.width))
    card.alpha_composite(avatar_title, (0, 1750))

    card = add_footer(card, 600)
    card = await convert_img(card)
    await bot.send(card)
