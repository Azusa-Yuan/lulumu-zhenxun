from nonebot import on_fullmatch
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message
from nonebot.permission import SUPERUSER
from utils.utils import scheduler, get_bot
from . import chara
from utils.http_utils import AsyncHttpx
import os
from services import logger
from utils.message_builder import image

__zx_plugin_name__ = "PCR_Chara_Update [Admin]"

__plugin_usage__ = """
""".strip()
__plugin_superuser_usage__ = """
usage：
    指令或者每日定时更新
    指令：
        update-pcr-chara
        重载花名册
        更新花名册
""".strip()
__plugin_cmd__ = [
    "重载花名册"
]
__plugin_version__ = 0.1
PCR_Chara_Update = on_fullmatch(('update-pcr-chara', '重载花名册', '更新花名册'), permission=SUPERUSER, priority=5, block=True)


@PCR_Chara_Update.handle()
async def pull_chara(bot: Bot, event: MessageEvent=None):
    try:
        rsp = await AsyncHttpx.get('https://raw.githubusercontent.com/Ice-Cirno/LandosolRoster/master/_pcr_data.py')
        rsp.raise_for_status()
        rsp = rsp.text

        filename = os.path.join(os.path.dirname(__file__), '_pcr_data.py')
        with open(filename, 'w', encoding='utf8') as f:
            f.write(rsp)
        result = chara.roster.update()

    except Exception as e:
        logger.exception(e)
        for superuser in bot.config.superusers:
            await bot.send_private_msg(
                user_id=superuser,
                message=f'pcr_data定时更新时遇到错误：\n{e}'
            )
        return
    result = f"角色别称导入成功 {result['success']}，重名 {result['duplicate']}"
    for superuser in bot.config.superusers:
        await bot.send_private_msg(
            user_id=superuser,
            message=f'pcr_data定时更新：\n{result}'
        )

@scheduler.scheduled_job(
    "cron",
    hour=5,
    minute=1,
)
async def _():
    bot = get_bot()
    await pull_chara(bot)

group_id_list = ["852670048", "522392057", "639706264"]
@scheduler.scheduled_job(
    "cron",
    hour=23,
    minute=50,
)
async def __():
    global group_id_list
    bot = get_bot()
    rst = f'今天的编年点了吗'
    rst = rst + image("other/biannian.jpg")
    for group_id in group_id_list:
        await bot.send_group_msg(group_id=group_id, message=Message(rst))

