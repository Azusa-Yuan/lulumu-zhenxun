from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageEvent
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from nonebot import require, on_command, on_message
from configs.path_config import IMAGE_PATH
from nonebot.params import CommandArg
from utils.message_builder import image
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver

__zx_plugin_name__ = "DNF"
__plugin_usage__ = """
usage：
    比例趋势 跨2
""".strip()
__plugin_des__ = "DNF"
__plugin_cmd__ = ["比例趋势"]
__plugin_type__ = ("一些工具",)


ReportRegions = {
    "跨1": 0,
    "跨2": 1,
    "跨3a": 2,
    "跨3b": 3,
    "跨4": 4,
    "跨5": 5,
    "跨6": 6,
    "跨7": 7,
    "跨8": 8
}

ReportRegions_2 = {
    "跨1": "1",
    "跨2": "2",
    "跨3a": "3a",
    "跨3b": "3b",
    "跨4": "4",
    "跨5": "5",
    "跨6": "6",
    "跨7": "7",
    "跨8": "8",
    "跨一": "1",
    "跨二": "2",
    "跨三A": "3a",
    "跨三B": "3b",
    "跨四": "4",
    "跨五": "5",
    "跨六": "6",
    "跨七": "7",
    "跨八": "8"
}

ReportSite = {
    1: "5173",
    11: "http://www.weiweiwang.com/",
    12: "http://www.3yx.com/",
    17: "uu898",
    21: "17uoo",
    30: "http://b2b.yxb321.com/share.action?shareResource=111114114",
    39: "http://www.151y.com/",
    40: "dd373",
    41: "http://www.dong10.com/",
    44: "7881",
    49: "52buff"
}

SiteChoices = [17, 40, 44]

DNFExRateTrend = on_command("比例趋势", priority=5, block=True)
DNFExRate = on_command("DNF比例", aliases={"比例", "游戏币比例", "游戏币", "金币"}, priority=5, block=True)
DNFMaodun = on_command("矛盾", priority=5, block=True)

tmpDNFExRateTrendPath = IMAGE_PATH / "DNFExRateTrend.png"
tmpDNFExRatePath = IMAGE_PATH / "DNFExRateTrend.png"


def DNFExRateTrend_(server, path):
    # data = requests.post("https://www.yxdr.com/bijia/coinsale", headers=header, data=param).content.decode("utf-8")
    if server not in ReportRegions:
        return False
    url_1 = "https://www.yxdr.com/bijiaqi/dnf/maodundejiejingti/hangqing"
    soup = BeautifulSoup(requests.get(url=url_1).text, 'html.parser')
    scripts = soup.find("body").find_all("script")
    url_2 = "https://www.yxdr.com/report/dnf/" + scripts[7]["src"].split('/')[-1]
    raw_data = requests.get(url=url_2).text.split("\r\n")[4: -1][ReportRegions[server]].split(":")[1][:-4]
    raw_data = eval(raw_data)

    x = []
    y = [[] for i in SiteChoices]

    for single_data in raw_data:
        if single_data[0] not in x:
            x.append(single_data[0])
        if single_data[1] in SiteChoices:
            single_data[2] = 1 / single_data[2]
            y[SiteChoices.index(single_data[1])].append(single_data[2])

    maxLen = len(x)

    plt.clf()
    # 做一个平均的填充
    y = [line + [sum(line) / len(line)] * (maxLen - len(line)) for line in y]

    # 绘制多条折线图
    for line in y:
        plt.plot(x, savgol_filter(line, window_length=len(line), polyorder=4))

    # 添加标题和坐标轴标签
    plt.title('DNF Exchange Rate')
    plt.xlabel('Time')
    plt.ylabel('Exchange Rate')
    # 显示图例
    plt.legend([ReportSite[i] for i in SiteChoices])
    # 显示网格线
    plt.grid(True)
    # 直接保存图片是为了通用性
    plt.savefig(path)
    return True


# 创建一个 Chrome WebDriver 对象

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')  # 无头模式，服务器没有图形界面这个必须
chrome_options.add_argument('--disable-gpu')  # 不需要gpu加速
chrome_options.add_argument('--no-sandbox')  # 这个配置很重要
driver = webdriver.Chrome(options=chrome_options)


async def DNFExRate_(server, productType):
    if server not in ReportRegions_2:
        return None

    # 加载网页
    url = f'https://www.yxdr.com/bijiaqi/dnf/{productType}/kua' + ReportRegions_2[server]  # 替换为你要截图的网页 URL
    driver.get(url)
    wait = WebDriverWait(driver, 10)  # 设置等待时间为10秒
    # 等待动态页面加载
    wait.until(EC.presence_of_element_located((By.ID, 'right_m')))

    # 获取网页高度
    # scroll_height = driver.execute_script("return document.documentElement.scrollHeight")
    # 设置浏览器窗口大小以适应整个网页内容
    driver.set_window_size(1000, 1500)
    # 保存网页截图以base64编码返回
    return url, driver.get_screenshot_as_base64()


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
