"""Ref: https://github.com/yuudi/yobot/blob/master/src/client/ybplugins/spider
GPLv3 Licensed. Thank @yuudi for his contribution!
"""
from utils.http_utils import AsyncHttpx
import abc
from dataclasses import dataclass
from typing import List, Union

from bs4 import BeautifulSoup


@dataclass
class Item:
    idx: Union[str, int]
    content: str = ""

    def __eq__(self, other):
        return self.idx == other.idx


class BaseSpider(abc.ABC):
    url = None
    src_name = None
    idx_cache = set()
    item_cache = []

    @classmethod
    async def get_response(cls) :
        resp = await AsyncHttpx.get(cls.url)
        resp.raise_for_status()
        return resp

    @staticmethod
    @abc.abstractmethod
    async def get_items(resp) :
        raise NotImplementedError

    @classmethod
    async def get_update(cls) :
        resp = await cls.get_response()
        items = await cls.get_items(resp)
        updates = [i for i in items if i.idx not in cls.idx_cache]
        if updates:
            cls.idx_cache.update(i.idx for i in items)
            cls.item_cache = items
        return updates

    @classmethod
    def format_items(cls, items) -> str:
        return f'{cls.src_name}新闻\n' + '\n'.join(map(lambda i: i.content, items))



class SonetSpider(BaseSpider):
    url = "http://www.princessconnect.so-net.tw/news/"
    src_name = "台服官网"

    @staticmethod
    async def get_items(resp):
        soup = BeautifulSoup(await resp.text, 'lxml')
        return [
            Item(idx=dd.a["href"],
                 content=f"{dd.text}\n▲www.princessconnect.so-net.tw{dd.a['href']}"
            ) for dd in soup.find_all("dd")
        ]



class BiliSpider(BaseSpider):
    url = "http://api.biligame.com/news/list?gameExtensionId=267&positionId=2&pageNum=1&pageSize=7&typeId="
    src_name = "B服官网"

    @staticmethod
    async def get_items(resp):
        content = resp.json()
        items = [
            Item(idx=n["id"],
                 content="{title}\n▲game.bilibili.com/pcr/news.html#detail={id}".format_map(n)
            ) for n in content["data"]
        ]
        return items
