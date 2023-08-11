import asyncio
import importlib
from io import BytesIO
from os.path import join
from services.log import logger
import pygtrie
from fuzzywuzzy import process
from PIL import Image
import unicodedata
import zhconv
from configs.path_config import IMAGE_PATH

# 将来放入util
def normalize_str(string) -> str:
    """
    规范化unicode字符串 并 转为小写 并 转为简体
    """
    string = unicodedata.normalize('NFKC', string)
    string = string.lower()
    string = zhconv.convert(string, 'zh-hans')
    return string


from . import _pcr_data

image_path = IMAGE_PATH / "priconne"
UNKNOWN = 1000
try:
    gadget_equip = Image.open(join(image_path, 'gadget/equip.png'))
    gadget_star = Image.open(join(image_path, 'gadget/star.png'))
    gadget_star_dis = Image.open(join(image_path, 'gadget/star_disabled.png'))
    gadget_star_pink = Image.open(join(image_path, 'gadget/star_pink.png'))
    unknown_chara_icon = Image.open(join(image_path, f'unit/icon_unit_{UNKNOWN}31.png'))
except Exception as e:
    logger.exception(e)


class Roster:

    def __init__(self):
        self._roster = pygtrie.CharTrie()
        self.update()

    def update(self):
        importlib.reload(_pcr_data)
        self._roster.clear()
        result = {'success': 0, 'duplicate': 0}
        for idx, names in _pcr_data.CHARA_NAME.items():
            for n in names:
                n = normalize_str(n)
                if n not in self._roster:
                    self._roster[n] = idx
                    result['success'] += 1
                else:
                    result['duplicate'] += 1
                    logger.warning(f'priconne.chara.Roster: 出现重名{n}于id{idx}与id{self._roster[n]}')
        return result

    def get_id(self, name):
        name = normalize_str(name)
        return self._roster[name] if name in self._roster else UNKNOWN

    def guess_id(self, name):
        """@return: id, name, score"""
        name, score = process.extractOne(name, self._roster.keys(), processor=normalize_str)
        return self._roster[name], name, score

    def parse_team(self, namestr):
        """@return: List[ids], unknown_namestr"""
        namestr = normalize_str(namestr.strip())
        team = []
        unknown = []
        while namestr:
            item = self._roster.longest_prefix(namestr)
            if not item:
                unknown.append(namestr[0])
                namestr = namestr[1:].lstrip()
            else:
                team.append(item.value)
                namestr = namestr[len(item.key):].lstrip()
        return team, ''.join(unknown)


roster = Roster()


def name2id(name):
    return roster.get_id(name)


def fromid(id_, star=0, equip=0):
    return Chara(id_, star, equip)


def fromname(name, star=0, equip=0):
    id_ = name2id(name)
    return Chara(id_, star, equip)


def guess_id(name):
    """@return: id, name, score"""
    return roster.guess_id(name)


def is_npc(id_):
    if id_ in _pcr_data.UnavailableChara:
        return True
    else:
        return not (1000 < id_ < 1900)


async def gen_team_pic(team, size=64, star_slot_verbose=True):
    num = len(team)
    des = Image.new('RGBA', (num*size, size), (255, 255, 255, 255))
    for i, chara in enumerate(team):
        src = chara.render_icon(size, star_slot_verbose)
        des.paste(src, (i * size, 0), src)
    return des


# async def download_chara_icon(id_, star):
#     url = f'https://redive.estertion.win/icon/unit/{id_}{star}1.webp'
#     save_path = R.img(f'priconne/unit/icon_unit_{id_}{star}1.png').path
#     logger.info(f'Downloading chara icon from {url}')
#     try:
#         rsp = await aiorequests.get(url, stream=True, timeout=5)
#     except Exception as e:
#         logger.error(f'Failed to download {url}. {type(e)}')
#         logger.exception(e)
#     if 200 == rsp.status_code:
#         img = Image.open(BytesIO(await rsp.content))
#         img.save(save_path)
#         logger.info(f'Saved to {save_path}')
#         return 0    # ok
#     else:
#         logger.error(f'Failed to download {url}. HTTP {rsp.status_code}')
#     return 1        # error


class Chara:

    def __init__(self, id_, star=0, equip=0):
        self.id = id_
        self.star = star
        self.equip = equip

    @property
    def name(self):
        return _pcr_data.CHARA_NAME[self.id][0] if self.id in _pcr_data.CHARA_NAME else _pcr_data.CHARA_NAME[UNKNOWN][0]

    @property
    def is_npc(self) -> bool:
        return is_npc(self.id)

    def get_icon(self, star=0):
        star = star or self.star
        star = 1 if 1 <= star < 3 else 3 if 3 <= star < 6 else 6
        res = Image.open(join(image_path, f'unit/icon_unit_{self.id}{star}1.png'))
        if not res:
            res = Image.open(join(image_path, f'unit/icon_unit_{self.id}31.png'))
        if not res:
            res = Image.open(join(image_path, f'unit/icon_unit_{self.id}11.png'))
        if not res:
            print(f'请下载{self.id} 资源')
            res = Image.open(join(image_path, f'unit/icon_unit_{self.id}{star}1.png'))
        if not res:
            res = Image.open(join(image_path, f'unit/icon_unit_{self.id}31.png'))
        if not res:
            res = Image.open(join(image_path, f'unit/icon_unit_{self.id}11.png'))
        if not res:
            res = Image.open(join(image_path, f'unit/icon_unit_{UNKNOWN}31.png'))
        return res

    async def get_icon_cqcode(self, star=0):
        return (await self.get_icon(star)).cqcode

    def render_icon(self, size, star_slot_verbose=True) -> Image:
        icon = self.get_icon()
        pic = icon.convert('RGBA').resize((size, size), Image.LANCZOS)

        l = size // 6
        star_lap = round(l * 0.15)
        margin_x = (size - 6*l) // 2
        margin_y = round(size * 0.05)
        if self.star:
            for i in range(5 if star_slot_verbose else min(self.star, 5)):
                a = i*(l-star_lap) + margin_x
                b = size - l - margin_y
                s = gadget_star if self.star > i else gadget_star_dis
                s = s.resize((l, l), Image.LANCZOS)
                pic.paste(s, (a, b, a+l, b+l), s)
            if 6 == self.star:
                a = 5*(l-star_lap) + margin_x
                b = size - l - margin_y
                s = gadget_star_pink
                s = s.resize((l, l), Image.LANCZOS)
                pic.paste(s, (a, b, a+l, b+l), s)
        if self.equip:
            l = round(l * 1.5)
            a = margin_x
            b = margin_x
            s = gadget_equip.resize((l, l), Image.LANCZOS)
            pic.paste(s, (a, b, a+l, b+l), s)
        return pic


# @sucmd('download-pcr-chara-icon', force_private=False, aliases=('下载角色头像'))
# async def download_pcr_chara_icon(sess: CommandSession):
#     '''
#     覆盖更新1、3、6星头像
#     '''
#     try:
#         ch = fromname(sess.current_arg_text.strip())
#         assert ch.id != UNKNOWN, '未知角色名'
#         await asyncio.gather(
#             download_chara_icon(ch.id, 6),
#             download_chara_icon(ch.id, 3),
#             download_chara_icon(ch.id, 1),
#         )
#         msg = await ch.get_icon_cqcode(6) + \
#             await ch.get_icon_cqcode(3) + \
#             await ch.get_icon_cqcode(1)
#         await sess.send(msg)
#     except Exception as e:
#         logger.exception(e)
#         await sess.send(f'Error: {type(e)}')


# @sucmd('download-star6-chara-icon', force_private=False, aliases=('下载六星头像', '更新六星头像'))
# async def download_star6_chara_icon(sess: CommandSession):
#     '''
#     尝试下载缺失的六星头像，已有头像不会被覆盖
#     '''
#     try:
#         tasks = []
#         for id_ in _pcr_data.CHARA_NAME:
#             if is_npc(id_):
#                 continue
#             res = R.img(f'priconne/unit/icon_unit_{id_}61.png')
#             if not res.exist:
#                 tasks.append(download_chara_icon(id_, 6))
#         ret = await asyncio.gather(*tasks)
#         succ = sum(r == 0 for r in ret)
#         await sess.send(f'ok! downloaded {succ}/{len(ret)} icons.')
#     except Exception as e:
#         logger.exception(e)
#         await sess.send(f'Error: {type(e)}')
