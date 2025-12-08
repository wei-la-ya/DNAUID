import json
from typing import Dict, List, Optional
from pathlib import Path

from ..utils.api.model import RoleShowForTool
from ..utils.resource.RESOURCE_PATH import (
    ID2NAME_PATH,
    CHAR_ALIAS_PATH,
    WEAPON_ALIAS_PATH,
)

char_alias_data: Dict[str, List[str]] = {}
weapon_alias_data: Dict[str, List[str]] = {}
id2name_data: Dict[str, str] = {}


async def rebuild_name_convert(role_show: RoleShowForTool, is_force: bool = False):
    global char_alias_data, weapon_alias_data, id2name_data
    old_char_alias_data = {} if is_force else _get_alias_data(CHAR_ALIAS_PATH)
    old_weapon_alias_data = {} if is_force else _get_alias_data(WEAPON_ALIAS_PATH)
    old_id2name_data = {} if is_force else _get_alias_data(ID2NAME_PATH)

    async def generate_alias_data(metadatas: List[Dict], alias_data: Dict[str, List[str]]):
        for meta in metadatas:
            name = meta["name"]
            if name not in alias_data or len(alias_data[name]) == 0:
                alias_data[name] = [name]

    role_metadatas = [{"name": i.name, "id": i.charId} for i in role_show.roleChars]
    await generate_alias_data(role_metadatas, old_char_alias_data)
    weapon_metadatas = [{"name": i.name, "id": i.weaponId} for i in role_show.langRangeWeapons + role_show.closeWeapons]
    await generate_alias_data(weapon_metadatas, old_weapon_alias_data)
    old_id2name_data = {str(i["id"]): i["name"] for i in role_metadatas + weapon_metadatas}

    if old_char_alias_data.items() != char_alias_data.items():
        char_alias_data = old_char_alias_data
        with open(CHAR_ALIAS_PATH, "w", encoding="utf-8") as f:
            json.dump(char_alias_data, f, ensure_ascii=False, indent=2)
    if old_weapon_alias_data.items() != weapon_alias_data.items():
        weapon_alias_data = old_weapon_alias_data
        with open(WEAPON_ALIAS_PATH, "w", encoding="utf-8") as f:
            json.dump(weapon_alias_data, f, ensure_ascii=False, indent=2)
    if old_id2name_data.items() != id2name_data.items():
        id2name_data = old_id2name_data
        with open(ID2NAME_PATH, "w", encoding="utf-8") as f:
            json.dump(id2name_data, f, ensure_ascii=False, indent=2)


async def refresh_name_convert(is_force: bool = False):
    from ..utils import dna_api
    from ..utils.api.model import DNARoleForToolRes
    from ..utils.name_convert import rebuild_name_convert

    dna_user = await dna_api.get_random_dna_user()
    if not dna_user:
        return False, "没有可用的DNA用户"
    role_show = await dna_api.get_default_role_for_tool(dna_user.cookie, dna_user.dev_code)
    if not role_show.is_success:
        return False, "获取角色列表信息失败"
    role_show = DNARoleForToolRes.model_validate(role_show.data)
    await rebuild_name_convert(role_show.roleInfo.roleShow, is_force=is_force)
    return True, "别名恢复成功"


def _get_alias_data(alias_path: Path):
    try:
        data = json.loads(alias_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        alias_path.write_text("{}", encoding="utf-8")
        return {}


def load_alias_data():
    global char_alias_data, weapon_alias_data, id2name_data

    char_alias_data = _get_alias_data(CHAR_ALIAS_PATH)
    weapon_alias_data = _get_alias_data(WEAPON_ALIAS_PATH)
    id2name_data = _get_alias_data(ID2NAME_PATH)


load_alias_data()


def alias_to_char_name(char_name: Optional[str]) -> Optional[str]:
    if not char_name:
        return None
    for i in char_alias_data:
        if (char_name in i) or (char_name in char_alias_data[i]):
            return i
    return None


def alias_to_char_name_list(char_name: str) -> List[str]:
    for i in char_alias_data:
        if (char_name in i) or (char_name in char_alias_data[i]):
            return char_alias_data[i]
    return []


def char_name_to_char_id(char_name: Optional[str]) -> Optional[str]:
    char_name = alias_to_char_name(char_name)
    for _id, _name in id2name_data.items():
        if _name == char_name:
            return _id
    return None


def alias_to_weapon_name(weapon_name: str) -> str:
    for i in weapon_alias_data:
        if (weapon_name in i) or (weapon_name in weapon_alias_data[i]):
            return i

    if "专武" in weapon_name:
        char_name = weapon_name.replace("专武", "")
        name = alias_to_char_name(char_name)
        weapon_name = f"{name}专武"

    for i in weapon_alias_data:
        if (weapon_name in i) or (weapon_name in weapon_alias_data[i]):
            return i

    return weapon_name


def alias_to_weapon_name_list(weapon_name: str) -> List[str]:
    for i in weapon_alias_data:
        if (weapon_name in i) or (weapon_name in weapon_alias_data[i]):
            return weapon_alias_data[i]
    return []


def all_weapon_list() -> List[str]:
    return list(weapon_alias_data.keys())


def all_char_list() -> List[str]:
    return list(char_alias_data.keys())
