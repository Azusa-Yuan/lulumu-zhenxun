import os
import random

from nonebot import on_notice
from nonebot.adapters.onebot.v11 import PokeNotifyEvent

from configs.path_config import IMAGE_PATH, RECORD_PATH
from services.log import logger
from utils.message_builder import image, poke, record

__zx_plugin_name__ = "戳一戳"

__plugin_usage__ = """
usage：
    戳一戳随机掉落语音或美图萝莉图
""".strip()
__plugin_des__ = "戳一戳发送语音美图萝莉图不美哉？"
__plugin_type__ = ("其他",)
__plugin_version__ = 0.1
__plugin_author__ = "HibiKier"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["戳一戳"],
}

poke__reply = [
    "lsp你再戳？",
    "连个可爱美少女都要戳的肥宅真恶心啊。",
    "你再戳！",
    "？再戳试试？",
    "别戳了别戳了再戳就坏了555",
    "我爪巴爪巴，球球别再戳了",
    "你戳你🐎呢？！",
    "那...那里...那里不能戳...绝对...",
    "(。´・ω・)ん?",
    "有事恁叫我，别天天一个劲戳戳戳！",
    "欸很烦欸！你戳🔨呢",
    "?",
    "再戳一下试试？",
    "???",
    "正在关闭对您的所有服务...关闭成功",
    "啊呜，太舒服刚刚竟然睡着了。什么事？",
    "正在定位您的真实地址...定位成功。轰炸机已起飞",
]



poke_ = on_notice(priority=5, block=False)


@poke_.handle()
async def _poke_event(event: PokeNotifyEvent):
    if event.self_id == event.target_id:
        rand = random.random()
        path = "lulumu"
        if rand <= 0.3 and len(os.listdir(IMAGE_PATH / "image_management" / path)) > 0:
            index = random.randint(
                0, len(os.listdir(IMAGE_PATH / "image_management" / path)) - 1
            )
            result = image(
                IMAGE_PATH / "image_management" / path / f"{index}.jpg"
            )
            logger.info(f"USER {event.user_id} 戳了戳我 回复: {index}  {result}")
            await poke_.send(result)

        elif 0.3 < rand < 0.6:
            voice = random.choice(os.listdir(RECORD_PATH / "dinggong"))
            result = record(RECORD_PATH / "dinggong" / voice)
            await poke_.send(result)
            await poke_.send(voice.split("_")[1])
            logger.info(
                f'USER {event.user_id} 戳了戳我 回复: {result} \n {voice.split("_")[1]}'
            )
        else:
            await poke_.send(poke(event.user_id))
