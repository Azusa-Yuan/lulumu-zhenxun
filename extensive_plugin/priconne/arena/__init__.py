import re
import time
import asyncio
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
from utils.message_builder import image
from nonebot.permission import SUPERUSER
from nonebot import on_command, on_fullmatch
from services.log import logger
from configs.path_config import IMAGE_PATH
from utils.image_utils import pic2b64
from utils.utils import FreqLimiter, get_message_img, scheduler, get_bot
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import MessageEvent, Bot, Message, MessageSegment
from . import spider
# import hoshino

# from hoshino.typing import *

from .. import chara
from .record import update_dic
from os.path import dirname, join, exists
import numpy as np 
import json
from io import BytesIO
import requests
import copy

import cv2

__zx_plugin_name__ = "PCR竞技场作业查询"
__plugin_usage__ = '''
[怎么拆] 接防守队角色名 查询竞技场解法 支持截图查询
# 图片多队查询时，优先级越高越好
# 默认台服 B服和日服为:B怎么拆，日怎么拆
'''.strip()
__plugin_des__ = "你怎么又在击剑啊?"
__plugin_type__ = ("PCR相关",)
__plugin_cmd__ = ["怎么拆"]
__plugin_version__ = 0.5
__plugin_author__ = "None"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    'cmd': __plugin_cmd__
}

from . import arena

tmp_arena_path = IMAGE_PATH / "tmp_arena.png"


# 拼接图像
def concat_pic(pics, border=5):
    num = len(pics)
    w, h = pics[0].size
    des = Image.new('RGBA', (w, num * h + (num-1) * border), (255, 255, 255, 255))
    for i, pic in enumerate(pics):
        des.paste(pic, (0, i * (h + border)), pic)
    return des

lmt = FreqLimiter(5)

aliases = ( '怎么解', '怎么打', '如何拆', '如何解', '如何打', 'jjc查询')
aliases_b = tuple('b' + a for a in aliases) + tuple('B' + a for a in aliases)
aliases_b = list(aliases_b)
aliases_b.append('bjjc')
aliases_tw = tuple('台' + a for a in aliases)
aliases_tw = list(aliases_tw)
aliases_tw.append('台jjc')
aliases_jp = tuple('日' + a for a in aliases)
aliases_jp = list(aliases_jp)
aliases_jp.append('日jjc')
aliases = list(aliases)
aliases_all = aliases + aliases_tw
aliases_b = set(aliases_b)
aliases_tw = set(aliases_tw)
aliases_jp = set(aliases_jp)
aliases_all = set(aliases_all)

icon_update = on_fullmatch(('icon_update'), permission=SUPERUSER, priority=5, block=True)
PCR_arena_Update = on_fullmatch(('竞技场更新卡池'), permission=SUPERUSER, priority=5, block=True)
arena_query_tw = on_command("怎么拆", aliases=aliases_all, block=True, priority=5)
arena_query_b = on_command("b怎么拆", aliases=aliases_b, block=True, priority=5)
arena_query_jp = on_command("日怎么拆", aliases=aliases_jp, block=True, priority=5)

image_path = IMAGE_PATH / "priconne"
try:
    thumb_up_i = Image.open(join(image_path, 'gadget/thumb-up-i.png')).resize((16, 16), Image.LANCZOS)
    thumb_up_a = Image.open(join(image_path, 'gadget/thumb-up-a.png')).resize((16, 16), Image.LANCZOS)
    thumb_down_i = Image.open(join(image_path, 'gadget/thumb-down-i.png')).resize((16, 16), Image.LANCZOS)
    thumb_down_a = Image.open(join(image_path, 'gadget/thumb-down-a.png')).resize((16, 16), Image.LANCZOS)
except Exception as e:
    logger.error(e)


@arena_query_tw.handle()
async def arena_query_tw_handle(bot,event: MessageEvent, arg: Message = CommandArg()):
    await _arena_query(bot, event, arg, region=3)


@arena_query_b.handle()
async def arena_query_b_handle(bot,event: MessageEvent, arg: Message = CommandArg()):
    await _arena_query(bot, event, arg, region=2)

@arena_query_jp.handle()
async def arena_query_jp_handle(bot,event: MessageEvent, arg: Message = CommandArg()):
    await _arena_query(bot, event, arg, region=4)


async def render_atk_def_teams(entries, border_pix=5):
    n = len(entries)
    icon_size = 64
    im = Image.new('RGBA', (5 * icon_size + 100, n * (icon_size + border_pix) - border_pix), (255, 255, 255, 255))
    font = ImageFont.truetype('msyh.ttc', 16)
    draw = ImageDraw.Draw(im)
    for i, e in enumerate(entries):
        y1 = i * (icon_size + border_pix)
        y2 = y1 + icon_size
        for j, c in enumerate(e['atk']):
            x1 = j * icon_size
            x2 = x1 + icon_size
            try:
                icon = await c.render_icon(icon_size)  # 如使用旧版hoshino（不返回结果），请去掉await
                im.paste(icon, (x1, y1, x2, y2), icon)
            except:
                icon = c.render_icon(icon_size)
                im.paste(icon, (x1, y1, x2, y2), icon)

        thumb_up = thumb_up_a if e['user_like'] > 0 else thumb_up_i
        thumb_down = thumb_down_a if e['user_like'] < 0 else thumb_down_i
        x1 = 5 * icon_size + 10
        x2 = x1 + 16
        im.paste(thumb_up, (x1, y1 + 12, x2, y1 + 28), thumb_up)
        im.paste(thumb_down, (x1, y1 + 39, x2, y1 + 55), thumb_down)
        #draw.text((x1, y1), e['qkey'], (0, 0, 0, 255), font)
        draw.text((x1 + 25, y1 + 10), f"{e['up']}", (0, 0, 0, 255), font)
        #draw.text((x1+25, y1+35), f"{e['down']}+{e['my_down']}" if e['my_down'] else f"{e['down']}", (0, 0, 0, 255), font)
        draw.text((x1 + 25, y1 + 35), f"{e['down']}", (0, 0, 0, 255), font)
    return im


async def getBox(img):
    img = img.convert("RGBA")
    boxDict, s = await getPos(img)
    return boxDict, s


curpath = dirname(__file__)

dataDir = join(curpath, 'dic.npy')
if not exists(dataDir):
    update_dic()
data = np.load(dataDir, allow_pickle=True).item()
data_processed = None


async def cut_image(image, hash_size=16):
    # 将图像缩小成(16+1)*16并转化成灰度图
    image1 = image.resize((hash_size + 1, hash_size), Image.ANTIALIAS).convert('L')
    pixel = list(image1.getdata())
    return pixel


async def trans_hash(lists):
    # 比较列表中相邻元素大小
    j = len(lists) - 1
    hash_list = []
    m, n = 0, 1
    for i in range(j):
        if lists[m] > lists[n]:
            hash_list.append(1)
        else:
            hash_list.append(0)
        m += 1
        n += 1
    return hash_list


async def difference_value(image_lists):
    # 获得图像差异值并获得指纹
    assert len(image_lists) == 17 * 16, "size error"
    m, n = 0, 17
    hash_list = []
    for i in range(0, 16):
        slc = slice(m, n)
        image_slc = image_lists[slc]
        hash_list.append(await trans_hash(image_slc))
        m += 17
        n += 17
    return hash_list


async def get_hash_arr(image):
    return np.array(await difference_value(await cut_image(image)))


async def calc_distance_arr(arr1, arr2):
    return sum(sum(abs(arr1 - arr2)))


async def calc_distance_img(image1, image2):
    return await calc_distance_arr(await get_hash_arr(image2) - await get_hash_arr(image1))


async def process_data():
    global data, data_processed
    data_processed = {}
    for uid in data:
        data_processed[uid] = await get_hash_arr(Image.fromarray(data[uid][25:96, 8:97, :]))


async def cutting(img, mode):
    im_grey = img.convert('L')
    totArea = (im_grey.size)[0] * (im_grey.size)[1]
    im_grey = im_grey.point(lambda x: 255 if x > 210 else 0)
    thresh = np.array(im_grey)

    # cv2.findContours. opencv3版本会返回3个值，opencv2和4只返回后两个值
    #img2, contours, hier = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contours, hier = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    img2 = thresh

    lis = []
    icon = []
    icon_area = {}
    for i in range(len(contours)):
        area = cv2.contourArea(contours[i])  # 计算轮廓面积，但是可能和像素点区域不太一样 收藏
        lis.append(area)
        if area > 500:
            if mode == 2:
                x, y, w, h = cv2.boundingRect(contours[i])
                if w / h > 0.95 and w / h < 1.05:
                    are = (w + h) // 2
                    areaRatio = are * are / totArea * 100
                    # print(f"{areaRatio:2f}%")
                    if areaRatio >= 0.5:
                        icon.append([are, [x, y, w, h]])
                        icon_area[are] = icon_area.setdefault(are, 0) + 1
    # print()
    if mode == 1:
        i = lis.index(max(lis))
        x, y, w, h = cv2.boundingRect(contours[i])
        #cv2.rectangle(img2, (x, y), (x + w, y + h), (153, 153, 0), 5)
        img3 = img2[y + 2:y + h - 2, x + 2:x + w - 2]
        img4 = Image.fromarray(img3)
        return img4, [x, y, w, h]
    if mode == 2:
        if icon_area == {}:
            return False
        icon_area = sorted(icon_area.items(), key=lambda x: x[1], reverse=True)
        # print(icon_area)
        accepted_area = [icon_area[0][0]]
        for i in icon_area:
            if abs(i[0] - accepted_area[0]) <= 5:
                accepted_area.append(i[0])
        # print(accepted_area)
        icon = list(sorted(map(lambda x: x[1], filter(lambda x: x[0] in accepted_area, icon)), key=lambda x: x[1] * 100000 + x[0]))
        # print(icon)
        return icon


async def cut(img, border):
    x, y, w, h = border
    img = np.array(img)
    img = img[y + 2:y + h - 2, x + 2:x + w - 2]
    img = Image.fromarray(img)
    return img


async def getPos(img):
    im_grey = img
    cnt = 0
    while cnt <= 5:
        bo = False
        cnt += 1
        border = await cutting(im_grey, 2)
        if border == False:
            bo = True
        else:
            border = sorted(border, key=lambda x: x[1] - x[0] * 10000)
            x, y, w, h = border[0]  # 列 行 宽 长
            img_border = img.crop([x + 2, y + 2, x + w - 2, y + h - 2])
            xpos = 1  # 列
            xlast = border[0][0]
            ypos = 1  # 行
            ylast = border[0][1]
            outpDict = {}
            if len(border) >= 5:
                for i in border:
                    x, y, w, h = i

                    if abs(x - xlast) > w // 2:
                        ypos = 1
                        xpos += 1

                    elif abs(y - ylast) > h // 2:
                        ypos += 1
                    xlast = x
                    ylast = y
                    if ypos in outpDict and len(outpDict[ypos]) >= 5:
                        continue
                    cropped = img.crop([x + 2, y + 2, x + w - 2, y + h - 2])
                    unit_id, unit_name = await getUnit(cropped)
                    if unit_name == "Unknown" or unit_id == 0:
                        pass
                    else:
                        outpDict[ypos] = [[unit_id, unit_name]] + outpDict.get(ypos, [])

                outpDict = list(sorted(outpDict.items(), key=lambda x: x[0]))
                outpList = []
                outpName = []
                for i in outpDict:
                    i = i[1]
                    if len(i) >= 5:
                        i = i[-5:]
                        lis = []
                        nam = []
                        for j in i:
                            lis.append(j[0])
                            nam.append(j[1])
                        outpList.append(copy.deepcopy(lis))
                        outpName.append(' '.join(nam))
                # print(outpList)
                outpName = "识别阵容为：\n" + '\n'.join(outpName)
                # print(outpName)
                if outpList != []:
                    return outpList, outpName

        im_grey, border = await cutting(im_grey, 1)
        if cnt == 1 or bo:
            im_grey = im_grey.point(lambda x: 0 if x > 128 else 255)
        img = await cut(img, border)
    return [], []


async def getUnit(img2):
    img2 = img2.convert("RGB").resize((128, 128), Image.ANTIALIAS)
    img3 = np.array(img2)
    img4 = img3[25:96, 8:97, :]
    img4 = Image.fromarray(img4)
    dic = {}
    global data_processed
    if data_processed == None:
        await process_data()

    img4_arr = await get_hash_arr(img4)
    for uid in data_processed:
        dic[uid] = await calc_distance_arr(data_processed[uid], img4_arr)

    lis = list(sorted(dic.items(), key=lambda x: abs(x[1])))
    if int(lis[0][1]) <= 92:
        mi = int(lis[0][1])
        for uid6, similarity in lis:
            uid = int(uid6) // 100
            similarity = int(similarity)
            if abs(similarity - mi) > 10:
                break
            name = "Unknown"
            try:
                nam = chara.fromid(uid).name
            except:
                pass
            print(f'{nam} {str(uid6)[-2]}x {100-similarity}% {uid6}')
        print()
        uid = int(lis[0][0]) // 100
        if int(lis[0][0]) == 108231 and int(lis[1][0]) == 100731 and int(lis[1][1]) - int(lis[0][1]) <= 5:
            uid = 1007
        try:
            nam = chara.fromid(uid).name
            return uid, nam
        except:
            return uid, "Unknown"
    return 0, "Unknown"


async def get_pic(address):
    return requests.get(address, timeout=20).content


async def _arena_query(bot, event: MessageEvent, arg: Message = CommandArg(), region: int = 2):
    arena.refresh_quick_key_dic()
    uid = event.user_id
    ret = ''

    if not lmt.check(uid):
        await bot.send(event, '您查询得过于频繁，请稍等片刻')
    lmt.start_cd(uid)
    # 处理输入数据
    defen = ""
    img = get_message_img(event.json())
    if img:
        await bot.send(event, "recognizing")
        image = Image.open(BytesIO(await get_pic(img[0])))
        boxDict, s = await getBox(image)
        if boxDict == []:
            await bot.send(event, "未识别到角色！")
        # print(s)
        # print(boxDict)
        try:
            await bot.send(event, s)
        except:
            pass

        if region == -20:
            return

        lis = []  # [[[第1队第1解],[第1队第2解]], [[第2队第1解]], []]
        if len(boxDict) == 1:
            await __arena_query(bot, event, arg, region, boxDict[0])
            return
        if len(boxDict) > 3:
            await bot.send(event, "请截图pjjc详细对战记录（对战履历详情）（含敌我双方2或3队阵容）")
        tot = 0
        for i in boxDict:
            li = []
            res = await __arena_query(bot, event, arg, region, i, 1)
            # print(res)
            if res == []:
                lis.append([])
            else:
                tot += 1
                for num, squad in enumerate(res):
                    # print(squad)
                    soutp = ""
                    squads = []
                    for nam in squad["atk"]:
                        # print(nam)
                        soutp += nam.name + " "
                        squads.append(nam.id)
                    num = int(squad["up"])*10 /(int(squad["down"]+int(squad["up"])+1))
                    if num < 4 :
                        num = -5
                    squads.append(num)
                    squads.append(soutp[:-1])
                    li.append(copy.deepcopy(squads))
                lis.append(copy.deepcopy(li))
            await asyncio.sleep(1)
        # print(lis)
        if tot == 0:
            await bot.send(event, "均未查询到解法！")
        if tot == 1:
            for num, i in enumerate(lis):
                if len(i) > 0:
                    await bot.send(event, f"仅第{num+1}队查询到解法！")
                    await __arena_query(bot, event, arg, region, boxDict[num])
            return
        le = len(lis)
        outp = ""
        cnt = 0
        if le == 3:
            s1 = lis[0]
            s2 = lis[1]
            s3 = lis[2]
            max_num = 0
            for x in s1:
                for y in s2:
                    for z in s3:
                        if cnt>= 3 and max_num > 22:
                            continue
                        temp = x[:-2] + y[:-2] + z[:-2]
                        if len(temp) == len(set(temp)):
                            cnt += 1
                            if cnt <= 10 and max_num < 22:
                                sum_num = x[-2]+y[-2]+z[-2]
                                if sum_num > max_num:
                                    max_num = sum_num
                                # print(x[-2],y[-2],z[-2])
                                outp += f"优先级：{sum_num:03.1f}\n第{1}队：{x[-1]}\n第{2}队：{y[-1]}\n第{3}队：{z[-1]}\n"
        if outp != "":
            outp = "三队无冲配队：\n" + outp
            print(outp)
            await bot.send(event, outp)
            return
        for i in range(le - 1):
            for j in range(i + 1, le):
                s1 = lis[i]
                s2 = lis[j]
                max_num = 0
                for x in s1:
                    for y in s2:
                        if cnt>= 3 and max_num > 15:
                            continue
                        if not (set(x[:-2]) & set(y[:-2])):
                            cnt += 1
                            if cnt < 10 :
                                sum_num = x[-2]+y[-2]
                                if sum_num > max_num:
                                    max_num = sum_num
                                outp += f"优先级：{sum_num:03.1f}\n第{i+1}队：{x[-1]}\n第{j+1}队：{y[-1]}\n"
        if outp != "":
            outp = "两队无冲配队：\n" + outp
            await bot.send(event, outp)
            return
        outp = "不存在无冲配队！"
        for num, i in enumerate(lis):
            if i != []:
                outp += f"\n第{num+1}队的解法为：\n"
                for j in i:
                    outp += j[-1] + "\n"
        await bot.send(event, outp)

    else:
        await __arena_query(bot, event, arg, region)


async def __arena_query(bot, event: MessageEvent, arg: Message = CommandArg(), region: int = 2, defen="", raw=0):
    uid = event.user_id
    unknown = ""
    if defen == "":
        defen = arg.extract_plain_text()
        defen = re.sub(r'[?？，,_]', '', defen)
        defen, unknown = chara.roster.parse_team(defen)

    if unknown:
        _, name, score = chara.guess_id(unknown)
        if score < 70 and not defen:
            return  # 忽略无关对话
        msg = f'无法识别"{unknown}"' if score < 70 else f'无法识别"{unknown}" 您说的有{score}%可能是{name}'
        await bot.send(event, msg)
    if not defen:
        await bot.send(event, '查询请发送"b/日/台jjc+防守队伍"，无需+号')
        return
    if len(defen) > 5:
        await bot.send(event, '编队不能多于5名角色')
        return
    if len(defen) < 5:
        await bot.send(event, '由于数据库限制，少于5名角色的检索条件请移步pcrdfans.com进行查询')
        return
    if len(defen) != len(set(defen)):
        await bot.send(event, '编队中含重复角色')
        return
    if any(chara.is_npc(i) for i in defen):
        return
    if 1004 in defen:
        await bot.send(event, '\n⚠️您正在查询普通版炸弹人\n※万圣版可用万圣炸弹人/瓜炸等别称')

    # print(defen)
    # 执行查询
    logger.info('Doing query...')
    res = None
    try:
        res = await arena.do_query(defen, uid, region, raw)
    except requests.HTTPError as e:
        code = e.response["code"]
        if code == 117:
            await bot.send(event, "高峰期服务器限流！请前往pcrdfans.com/battle")
            return
        else:
            await bot.send(event, f'code{code} 查询出错\n请先前往pcrdfans.com进行查询')
            return
    logger.info('Got response!')

    # 处理查询结果
    if res is None:
        if not raw:
            await bot.send(event, '数据库未返回数据，请再次尝试查询或前往pcrdfans.com')
            return
        else:
            return []
    if not len(res):
        if not raw:
            await bot.send(event, '抱歉没有查询到解法\n作业上传请前往pcrdfans.com')
            return
        else:
            return []
    res = res[:min(8, len(res))]  # 限制显示数量，截断结果
    if raw:
        return res
    # print(res)

    # 发送回复
    logger.info('Arena generating picture...')
    teams = await render_atk_def_teams(res)
    teams.save(tmp_arena_path)
    logger.info('Arena picture ready!')
    # 纯文字版
    # atk_team = '\n'.join(map(lambda entry: ' '.join(map(lambda x: f"{x.name}{x.star if x.star else ''}{'专' if x.equip else ''}" , entry['atk'])) , res))

    # details = [" ".join([
    #     f"赞{e['up']}+{e['my_up']}" if e['my_up'] else f"赞{e['up']}",
    #     f"踩{e['down']}+{e['my_down']}" if e['my_down'] else f"踩{e['down']}",
    #     e['qkey'],
    #     "你赞过" if e['user_like'] > 0 else "你踩过" if e['user_like'] < 0 else ""
    # ]) for e in res]

    # defen = [ chara.fromid(x).name for x in defen ]
    # defen = f"防守方【{' '.join(defen)}】"
    at = str(MessageSegment.at(event.user_id))

    msg = (f'已为骑士君查询到以下进攻方案：\n'
        + image("tmp_arena.png"))
        # defen,
        # '作业评价：',
        # *details,
        # '※发送"点赞/点踩"可进行评价'
    
    if region == 3:
        msg = msg+'※使用"b怎么拆"或"日怎么拆"可按服过滤\n'
    # msg = msg+'https://www.pcrdfans.com/battle'

    logger.debug('Arena sending result...')
    await bot.send(event, msg)
    logger.debug('Arena result sent!')


rex_qkey = re.compile(r'^[0-9a-zA-Z]{5}$')


@PCR_arena_Update.handle()
async def _update_dic():
    try:
        msg = update_dic()
        await PCR_arena_Update.finish(msg)
        global data
        data = np.load(dataDir, allow_pickle=True).item()
        await process_data()
    except Exception as e:
        await PCR_arena_Update.finish(f'Error: {e}')



@icon_update.handle()
async def icon_update_(bot: Bot, type:bool=True):
    icon_spider = spider.Spider()
    msg = icon_spider.download_icon_unit()
    if msg == '':
        msg = "没有需要更新的角色"
    icon_update.finish(msg)


@scheduler.scheduled_job(
    "cron",
    day_of_week='0',
    hour=2,
    minute=30,
)
async def _():
    bot = get_bot()
    flag = False
    for superuser in bot.config.superusers:
        await bot.send_private_msg(
            user_id=superuser,
            message="开始更新icon"
        )

    icon_spider = spider.Spider()
    msg = icon_spider.download_icon_unit()
    if msg == '':
        msg = "没有需要更新的icon"
        flag = True
    for superuser in bot.config.superusers:
        await bot.send_private_msg(
            user_id=superuser,
            message=msg
        )
    if flag:
        return
    try:
        msg = update_dic()
        for superuser in bot.config.superusers:
            await bot.send_private_msg(
                user_id=superuser,
                message=msg
            )
        global data
        data = np.load(dataDir, allow_pickle=True).item()
        await process_data()
    except Exception as e:
        for superuser in bot.config.superusers:
            await bot.send_private_msg(
                user_id=superuser,
                message=f'Error: {e}'
            )

