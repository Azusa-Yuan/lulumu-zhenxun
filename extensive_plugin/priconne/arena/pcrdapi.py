from ctypes import CDLL, CFUNCTYPE, POINTER, c_int, c_char_p, c_ubyte
from random import choices
from time import time
from platform import architecture
from json import dumps
from os.path import join, dirname
# from hoshino.aiorequests import post
from utils.http_utils import AsyncHttpx
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.66",
    "Referer": "https://pcrdfans.com/",
    "Origin": "https://pcrdfans.com",
    "Accept": "*/*",
    "Content-Type": "application/json; charset=utf-8",
    "Authorization": "",
    "Host": "api.pcrdfans.com",
}

def _getNonce():
    return ''.join(choices("0123456789abcdefghijklmnopqrstuvwxyz", k=16))

def _getTs():
    return int(time())

def _dumps(x):
    return dumps(x, ensure_ascii=False).replace(' ', '')

_dllname = join(dirname(__file__), 'libpcrdwasm.so')
_getsign = CDLL(_dllname).getSign
_getsign.restype = POINTER(c_ubyte)

async def callPcrd(_def, page, region, sort, proxies=None):
    data = {
        "def": _def,
        "language": 0,
        "nonce": _getNonce(),
        "page": page,
        "region": region,
        "sort": sort,
        "language": 0,
        "ts": _getTs()
    }

    gsign = _getsign(_dumps(data).encode('utf8'), data["nonce"].encode('utf8'))
    list = []
    for n in range(255):
        if gsign[n] == 0:
            break
        list.append(gsign[n])
    data["_sign"] = bytes(list).decode('utf8')
    resp = await AsyncHttpx.post("https://api.pcrdfans.com/x/v1/search", headers=headers, data=_dumps(data).encode('utf8'))
    return  resp.json()


def callPcrdSync(_def, page, region, sort, proxies=None):
    data = {
        "def": _def,
        "language": 0,
        "nonce": _getNonce(),
        "page": page,
        "region": region,
        "sort": sort,
        "ts": _getTs()
    }

    gsign = _getsign(_dumps(data).encode('utf8'), data["nonce"].encode('utf8'))
    list = []
    for n in range(255):
        if gsign[n] == 0:
            break
        list.append(gsign[n])
    data["_sign"] = bytes(list).decode('utf8')
    resp = AsyncHttpx.post("https://api.pcrdfans.com/x/v1/search", headers=headers, data=_dumps(data).encode('utf8'))
    return resp.json()

'''
from nonebot import on_startup
@on_startup
async def startup():
    print(await callPcrd([170101,107801,100701,104501,102901], 1, 1, 1, {
    "https": "localhost:1080"}))
'''
'''
print(callPcrdSync([106301, 109201, 109301, 101101, 101601], 1, 2, 1,{
    "https": "localhost:1080"}))
    '''