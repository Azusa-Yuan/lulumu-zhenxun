from msgpack import packb, unpackb
from random import randint
from Crypto.Cipher import AES
from hashlib import md5, sha1
from Crypto.Util.Padding import unpad, pad
from base64 import b64encode, b64decode
from random import choice
import os
import json
import aiohttp
import asyncio
from copy import deepcopy
from asyncio import Lock


qlck = Lock()


# 获取headers
def get_headers():
    # app_ver = get_ver()
    default_headers = {
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/octet-stream',
        'User-Agent': 'Dalvik/2.1.0 (Linux, U, Android 5.1.1, PCRT00 Build/LMY48Z)',
        'Expect': '100-continue',
        'X-Unity-Version': '2018.4.21f1',
        'APP-VER': "4.1.0",
        'BATTLE-LOGIC-VERSION': '4',
        'BUNDLE-VER': '',
        'DEVICE': '2',
        'DEVICE-ID': '7b1703a5d9b394e24051d7a5d4818f17',
        'DEVICE-NAME': 'OPPO PCRT00',
        'GRAPHICS-DEVICE-NAME': 'Adreno (TM) 640',
        'IP-ADDRESS': '10.0.2.15',
        'KEYCHAIN': '',
        'LOCALE': 'Jpn',
        'PLATFORM-OS-VERSION': 'Android OS 5.1.1 / API-22 (LMY48Z/rel.se.infra.20200612.100533)',
        'REGION-CODE': '',
        'RES-VER': '00017004'
    }
    return default_headers


# unable to get correct version
# def get_ver():
#     app_url = 'https://apkimage.io/?q=tw.sonet.princessconnect'
#     app_res = requests.get(app_url, timeout=15)
#     soup = BeautifulSoup(app_res.text, 'lxml')
#     ver_tmp = soup.find('span', text=re.compile(r'Version：(\d\.\d\.\d)'))
#     app_ver = ver_tmp.text.replace('Version：', '')
#     return str(app_ver)


class ApiException(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


class pcrclient:

    @staticmethod
    def _makemd5(str) -> str:
        return md5((str + 'r!I@nt8e5i=').encode('utf8')).hexdigest()

    # acinfo_2cx['UDID'], acinfo_2cx['SHORT_UDID_lowBits'], acinfo_2cx['VIEWER_ID_lowBits'],acinfo_2cx[
    # 'TW_SERVER_ID'], pinfo['proxy']
    def __init__(self, udid, short_udid, viewer_id, platform, proxy):

        self.viewer_id = viewer_id
        self.short_udid = short_udid
        self.udid = udid
        self.headers = {}
        self.proxy = proxy

        header_path = os.path.join(os.path.dirname(__file__), 'headers.json')
        with open(header_path, 'r', encoding='UTF-8') as f:
            defaultHeaders = json.load(f)
        for key in defaultHeaders.keys():
            self.headers[key] = defaultHeaders[key]

        self.headers['SID'] = pcrclient._makemd5(viewer_id + udid)
        self.apiroot = f'https://api{"" if platform == "1" else "5"}-pc.so-net.tw'
        self.headers['platform'] = '1'

        self.shouldLogin = True

    @staticmethod
    def createkey() -> bytes:
        # 在这个表达式中，ord('0123456789abcdef'[randint(0, 15)]) 随机选择了 '0123456789abcdef'
        # 字符中的一个，然后将其转换为字节的整数值。然后，for _ in range(32) 循环用于生成32个这样的随机字节。
        return bytes([ord('0123456789abcdef'[randint(0, 15)]) for _ in range(32)])

    async def updateVersion(self, verison):
        print("当前版本为" + self.headers["APP-VER"] + "更改为" + verison)
        self.headers["APP-VER"] = verison
        return

    def _getiv(self) -> bytes:
        return self.udid.replace('-', '')[:16].encode('utf8')

    def pack(self, data: object, key: bytes) -> tuple:
        # 使用 msgpack 库将数据打包为字节流 默认使用utf-8编码 类似json吧  
        packed = packb(data,
            use_bin_type=False
        )
        # 字节流数据及加密后的产物
        return packed, self.encrypt(packed, key)

    def encrypt(self, data: bytes, key: bytes) -> bytes:
        # 创建AES加密器，使用CBC模式和指定的初始化向量iv
        aes = AES.new(key, AES.MODE_CBC, self._getiv())
        return aes.encrypt(pad(data, 16)) + key

    def decrypt(self, data: bytes):
        data = b64decode(data.decode('utf8'))
        aes = AES.new(data[-32:], AES.MODE_CBC, self._getiv())
        return aes.decrypt(data[:-32]), data[-32:]

    def unpack(self, data: bytes):
        data, key = self.decrypt(data)
        dec = unpad(data, 16)
        return unpackb(dec,
            strict_map_key = False
        ), key

    alphabet = '0123456789'

    @staticmethod
    def _encode(dat: str) -> str:
        return f'{len(dat):0>4x}' + ''.join([(chr(ord(dat[int(i / 4)]) + 10) if i % 4 == 2 else choice(pcrclient.alphabet)) for i in range(0, len(dat) * 4)]) + pcrclient._ivstring()

    @staticmethod
    def _ivstring() -> str:
        return ''.join([choice(pcrclient.alphabet) for _ in range(32)])

    async def callapi(self, apiurl: str, request: dict, noerr: bool = False, delay: float = 0):
        if delay > 1:
            await asyncio.sleep(delay/1000)
        # 32个随机字节
        key = pcrclient.createkey()
        
        # 深拷贝 这样调用callapi不需要加锁
        header = deepcopy(self.headers)

        try:
            if self.viewer_id is not None:
                request['viewer_id'] = b64encode(self.encrypt(str(self.viewer_id).encode('utf8'), key))
            packed, crypted = self.pack(request, key)
            header['PARAM'] = sha1((self.udid + apiurl + b64encode(packed).decode('utf8') + str(self.viewer_id)).encode('utf8')).hexdigest()
            header['SHORT-UDID'] = pcrclient._encode(self.short_udid)

            if len(self.proxy) > 1:
                async with aiohttp.ClientSession(headers=header) as session:
                    # 最终url由self.apiroot 和 apiurl构成
                    async with session.post(self.apiroot + apiurl, proxy=self.proxy, data=crypted) as resp:
                        response = await resp.read()
            else:
                async with aiohttp.ClientSession(headers=header) as session:
                    async with session.post(self.apiroot + apiurl, data=crypted) as resp:
                        response = await resp.read()

            response = self.unpack(response)[0]

            data_headers = response['data_headers']

            if 'viewer_id' in data_headers:
                self.viewer_id = data_headers['viewer_id']

            if 'required_res_ver' in data_headers:
                async with qlck:
                    self.headers['RES-VER'] = data_headers['required_res_ver']

            data = response['data']
            if not noerr and 'server_error' in data:
                data = data['server_error']
                code = data_headers['result_code']
                print(f'pcrclient: {apiurl} api failed code = {code}, {data}')
                raise ApiException(data['message'], data['status'])
            return data

            # 生成角色信息json文件，用于调试
            # json_data = json.dumps(data, indent=4, ensure_ascii=False)
            # data_path =  Path(__file__).parent / 'res_data.json'
            # data_path.write_text(json_data, encoding="utf-8")

        except Exception as e:
            raise

    async def login(self):

        await self.callapi('/check/check_agreement', {})
        await self.callapi('/check/game_start', {})
        await self.callapi('/load/index', {
            'carrier': 'Android'
        })

        self.shouldLogin = False
