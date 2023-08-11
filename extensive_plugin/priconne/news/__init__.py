from .spider import *
from services.log import logger
from nonebot import on_fullmatch
from nonebot.adapters.onebot.v11 import MessageEvent, Bot
__zx_plugin_name__ = "PCR新闻"
__plugin_usage__ = '''
Usage:
    [台服新闻] [B服新闻]
'''.strip()
__plugin_des__ = "台服新闻"
__plugin_type__ = ("PCR相关",)
__plugin_cmd__ = ["台服新闻",
                  '台服日程',
                  'B服新闻',
                  'b服新闻', 
                  'B服日程', 
                  'b服日程'
                    ]
__plugin_version__ = 0.5
__plugin_author__ = "None"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    'cmd': __plugin_cmd__
}

svtw = on_fullmatch(('台服新闻', '台服日程') ,block=True, priority=5)
svbl = on_fullmatch(('B服新闻', 'b服新闻', 'B服日程', 'b服日程'), block=True, priority=5)

async def news_poller(spider:BaseSpider,  TAG):
    if not spider.item_cache:
        await spider.get_update()
        logger.info(f'{TAG}新闻缓存为空，已加载至最新')
        return
    news = await spider.get_update()
    if not news:
        logger.info(f'未检索到{TAG}新闻更新')
        return
    logger.info(f'检索到{len(news)}条{TAG}新闻更新！')
    await broadcast(spider.format_items(news), TAG, interval_time=0.5)
    
# @svtw.scheduled_job('cron', minute='*/5', jitter=20)
# async def sonet_news_poller():
#     await news_poller(SonetSpider, svtw, '台服官网')

# @svbl.scheduled_job('cron', minute='*/5', jitter=20)
# async def bili_news_poller():
#     await news_poller(BiliSpider, svbl, 'B服官网')


async def send_news(bot, ev, spider:BaseSpider, max_num=5):
    if not spider.item_cache:
        await spider.get_update()
    news = spider.item_cache
    news = news[:min(max_num, len(news))]
    await bot.send(ev, spider.format_items(news))

@svtw.handle()
async def send_sonet_news(bot, event: MessageEvent):
    await send_news(bot, event, SonetSpider)

@svbl.handle()
async def send_bili_news(bot, event: MessageEvent):
    await send_news(bot, event, BiliSpider)
