import pickle
from os import path, listdir
from random import choice

from PIL import Image

from nonebot import on_fullmatch
from utils.utils import  DailyNumberLimiter
from utils.image_utils import pic2b64
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from .data_source import drawing, load_config
from .good_luck import GOOD_LUCK
__zx_plugin_name__ = "PCR运势"

__plugin_usage__ = """
usage：
    [抽签|人品|运势|占卜]
    随机角色预测今日运势
    准确率高达114.514%！
""".strip()

__plugin_cmd__ = [
    "抽签",
    "运势",
]
__plugin_type__ = ("PCR相关", )
__plugin_version__ = 0.1


_lmt = DailyNumberLimiter(1)
_divines = {}
conf_path = path.join(path.dirname(__file__), 'user_conf')
try:
    with open(conf_path, 'rb') as f:
        user_conf_dic = pickle.load(f)
except FileNotFoundError:
    user_conf_dic = {}


divine = on_fullmatch(('抽签', '运势', '占卜', '人品'),  priority=5, block=True)


@divine.handle()
async def divine_handle(bot, ev: MessageEvent):
    global _divines
    uid = ev.user_id
    if not _lmt.check(uid):
        await divine.finish(f'您今天抽过签了，再给您看一次哦'+_divines[uid])
    
    _lmt.increase(uid)

    base_dir = path.join(path.dirname(__file__), 'data', 'pcr')
    img_dir = path.join(base_dir, 'img')
    copywriting = load_config(path.join(base_dir, 'copywriting.json'))
    copywriting = choice(copywriting['copywriting'])

    if copywriting.get('type'): # 有对应的角色文案
        luck_type = choice(copywriting['type'])
        good_luck = luck_type['good-luck']
        content = luck_type['content']
        title = GOOD_LUCK[good_luck]
        chara_id = choice(copywriting['charaid'])
        img_name = f'frame_{chara_id}.jpg'
    else:
        good_luck = copywriting.get('good-luck')
        content = copywriting.get('content')
        title = GOOD_LUCK[good_luck]
        img_name = choice(listdir(img_dir))
        

    # 添加文字
    img = Image.open(path.join(img_dir, img_name))
    title_font_path = path.join(path.dirname(__file__),  'font', 'Mamelon.otf')
    text_font_path = path.join(path.dirname(__file__),  'font', 'sakura.ttf')
    img = drawing(img, title, content, title_font_path, text_font_path)

    b64_str = pic2b64(img)
    pic = MessageSegment.image(b64_str)
    _divines[uid] = pic
    await divine.finish(pic)







