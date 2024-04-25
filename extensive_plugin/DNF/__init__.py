from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageEvent
from nonebot import require, on_command, on_message
from nonebot.params import CommandArg
from utils.message_builder import image
from utils.utils import scheduler, get_bot

from .exchange import DNFExRate_, DNFExRateTrend_, tmpDNFExRateTrendPath, tmpDNFExRatePath
from .news import colg_news, new_scheduled_job

__zx_plugin_name__ = "DNF"
__plugin_usage__ = """
usage：
    比例趋势 跨2
""".strip()
__plugin_des__ = "DNF"
__plugin_cmd__ = ["比例趋势"]
__plugin_type__ = ("一些工具",)


DNFExRateTrend = on_command("比例趋势", priority=5, block=True)
DNFExRate = on_command("DNF比例", aliases={"比例", "游戏币比例", "游戏币", "金币"}, priority=5, block=True)
DNFMaodun = on_command("矛盾", priority=5, block=True)
colg_zixun = on_command("colg资讯", priority=5, block=True)


@DNFExRateTrend.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    server = arg.extract_plain_text().strip()
    if not server:
        return
    if DNFExRateTrend_(server, tmpDNFExRateTrendPath):
        await DNFExRateTrend.finish(image("DNFExRateTrend.png"))
    return


@DNFExRate.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    server = arg.extract_plain_text().strip()
    if not server:
        return
    try:
        url, base64_data = await DNFExRate_(server, 'youxibi')
        if base64_data == None:
            return
    except:
        await DNFExRate.finish("超时")

    await DNFExRate.finish(image("base64://" + base64_data) + url)


@DNFMaodun.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    server = arg.extract_plain_text().strip()
    if not server:
        return
    url, base64_data = await DNFExRate_(server, 'maodundejiejingti')
    if base64_data == None:
        return
    await DNFMaodun.finish(image("base64://"+base64_data) + url)


@colg_zixun.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    await colg_zixun.finish(await colg_news())


group_id_list = ["852670048", "233711588", "639706264"]
qq_id_list = ["1043728417", "1521039037"]


@scheduler.scheduled_job(
    "interval",
    minutes=3,
)
async def __():
    bot = get_bot()
    news_list = await new_scheduled_job()
    for context in news_list:
        for group_id in group_id_list:
            await bot.send_group_msg(group_id=group_id, message=context)
        for user_id in qq_id_list:
            await bot.send_private_msg(
                user_id=user_id,
                message=context
            )
