from json import load, dump
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, Message, MessageSegment
from nonebot.params import RegexGroup, CommandArg
from typing import Any, Tuple
from os.path import dirname, join, exists
from copy import deepcopy
from traceback import format_exc
from .playerpref import decryptxml
from .jjchistory import *
from .pcrjjc import *
from nonebot import on_regex, on_command, on_fullmatch
import re
from utils.utils import scheduler, get_bot
import shlex


__zx_plugin_name__ = "PCR"
__plugin_usage__ = """
usage：
    pcr
""".strip()
__plugin_des__ = "PCR"
__plugin_cmd__ = ["PCR"]
__plugin_type__ = ("其他",)
__plugin_version__ = 0.1
__plugin_author__ = "ice"

'''
轮询时的post改为协程并发，再次大幅加速，batch_size=4，为测试服务器相对较优的参数，
测试服务器单post收发延迟为500ms，自己服务器的较优参数请自行测试

'''
sv_help = '''
注意：数字2为服务器编号，仅支持2~4服

[竞技场bind 10位uid] 默认双场均启用，排名下降时推送 也可使用[竞技场bind 2 9位uid]
[竞技场查询 10位uid] 查询（bind后无需输入2 uid，可缩写为jjccx、看看） 也可使用[竞技场bind 2 9位uid]
[停止竞技场bind] 停止jjc推送
[停止公主竞技场bind] 停止pjjc推送
[启用竞技场bind] 启用jjc推送
[启用公主竞技场bind] 启用pjjc推送
[竞技场历史] jjc变化记录（bind开启有效，可保留10条）
[公主竞技场历史] pjjc变化记录（bind开启有效，可保留10条）
[详细查询 10位uid] 能不用就不用（bind后无需输入2 uid） 也可使用[详细查询 2 9位uid]
[竞技场关注 10位uid] 默认双场均启用，排名变化及上线时推送 也可使用[竞技场关注 2 9位uid]
[删除竞技场bind] 删除bind
[删除关注 x] 删除第x个关注
[竞技场bind状态] 查看排名变动推送bind状态
[关注列表] 返回关注的序号以及对应的游戏UID
[关注查询 x] 查询第x个关注 可缩写为看看

'''.strip()

sv_help = '''
注意：数字2为服务器编号，仅支持2~4服

[竞技场bind 10位uid] 默认双场均启用，排名下降时推送 也可使用[竞技场bind 2 9位uid]
[竞技场查询 10位uid] 查询（bind后无需输入2 uid，可缩写为jjccx、看看） 也可使用[竞技场bind 2 9位uid]
[停止竞技场bind] 停止jjc推送
[停止公主竞技场bind] 停止pjjc推送
[启用竞技场bind] 启用jjc推送
[启用公主竞技场bind] 启用pjjc推送
[竞技场历史] jjc变化记录（bind开启有效，可保留10条）
[公主竞技场历史] pjjc变化记录（bind开启有效，可保留10条）
[详细查询 10位uid] 能不用就不用（bind后无需输入2 uid） 也可使用[详细查询 2 9位uid]
[竞技场关注 10位uid] 默认双场均启用，排名变化及上线时推送 也可使用[竞技场关注 2 9位uid]
[删除竞技场bind] 删除bind
[删除关注 x] 删除第x个关注
[竞技场bind状态] 查看排名变动推送bind状态
[关注列表] 返回关注的序号以及对应的游戏UID
[关注查询 x] 查询第x个关注 可缩写为看看

'''.strip()

userQuery = on_command('竞技场查询',aliases={"看看", "jjccx", "关注查询"}, priority=5, block=True)
jjcBind = on_command("竞技场bind", priority=5, block=True)
jjcObserver = on_command("竞技场关注", priority=5, block=True)
help = on_fullmatch(("竞技场帮助"),  priority=5, block=True)
observerList = on_fullmatch(("关注列表"),  priority=5, block=True)
jjcUnbind = on_command('删除竞技场bind', priority=5, block=True)
deleteGroup = on_command('清理账号', priority=5, block=True)
delObserver = on_command('删除关注', priority=5, block=True)
updatePCRVersion = on_command('更新版本', priority=5, block=True)

bot = get_bot()


@help.handle()
async def _(event: MessageEvent):
    await help.finish(f'{sv_help}')

#------------------------------查询相关-------------------------------#
@userQuery.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    context = arg.extract_plain_text()
    pattern = re.compile(r'\s*(\d)?\s*(\d{9})?$')
    match = re.search(pattern, context)
    
    cx = match.group(1)
    id = match.group(2)
    
    uid = str(event.user_id)
    
    # at玩家会发生什么事情
    if id is None and cx is None:
        msg = event.get_message()
        for msg_seg in msg:
            if msg_seg.type == "at":
                uid = str(msg_seg.data['qq'])
                
    
    res, err = await pcrjjc.user_query(cx, id, uid)
    
    if err is not None:
        if isinstance(event, GroupMessageEvent):
            gid = str(event.group_id)
            err = f"[CQ:at,qq={uid}]{err}"
        await userQuery.send(err)
    else:
        if isinstance(event, GroupMessageEvent):
            gid = str(event.group_id)
            res = f"[CQ:at,qq={uid}]\r\n{res}"
            await bot.send_group_msg(group_id=gid, message=res)
        else:
            await bot.send_private_msg(user_id=uid, message=res)

@observerList.handle()
async def _(event: MessageEvent):
    uid = str(event.user_id)
   
    msg = await pcrjjc.observer_list(uid)
    await observerList.finish(msg)
    

#------------------------------绑定相关-------------------------------#
@jjcBind.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    global bot
    context = arg.extract_plain_text()
    pattern = re.compile(r'\s*(\d)\s*(\d{9})$')
    match = re.search(pattern, context)
    
    if match is None:
        await jjcBind.finish("请输入正确的uid")
    
    cx = match.group(1)
    id = match.group(2)
    # qq号
    uid = str(event.user_id)
    
    if isinstance(event, GroupMessageEvent):
        gid = str(event.group_id)
    else:
        gid = ""
    
    res, err = await pcrjjc.bind(cx, id, uid, gid)
    
    if err is not None:
        if isinstance(event, GroupMessageEvent):
            gid = str(event.group_id)
            err = f"[CQ:at,qq={uid}]{err}"
        await userQuery.send(err)
    else:
        if isinstance(event, GroupMessageEvent):
            gid = str(event.group_id)
            res = f"[CQ:at,qq={uid}]{res}"
            await bot.send_group_msg(group_id=gid, message=res)
        else:
            await bot.send_private_msg(user_id=uid, message=res) 
            
@jjcUnbind.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    uid = str(event.user_id)
    
    # 判断是否为QQ
    def is_qq(msg: str):
        return msg.isdigit() and 11 >= len(msg) >= 5
    
    # superusers拥有删除任意用户的权限
    if str(event.user_id) in bot.config.superusers:
        msg = event.get_message()
        for msg_seg in msg:
            if msg_seg.type == "at":
                uid = str(msg_seg.data['qq'])
            elif msg_seg.type == "text":
                raw_text = str(msg_seg)
                try:
                    texts = shlex.split(raw_text)
                except:
                    texts = raw_text.split()
                for text in texts:
                    if is_qq(text):
                        uid = text
                        
    msg = await pcrjjc.delete_sub(uid)      
    
    if isinstance(event, GroupMessageEvent):
            gid = str(event.group_id)
            res = f"[CQ:at,qq={str(event.user_id)}]{res}"
            await bot.send_group_msg(group_id=gid, message=msg)
    else:
        await bot.send_private_msg(user_id=uid, message=msg)               


@jjcObserver.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    global bot
    context = arg.extract_plain_text()
    pattern = re.compile(r'\s*(\d)\s*(\d{9})$')
    match = re.search(pattern, context)
    
    if match is None:
        await jjcBind.finish("请输入正确的uid")
    
    cx = match.group(1)
    id = match.group(2)
    uid = str(event.user_id)
    
    if isinstance(event, GroupMessageEvent):
        gid = str(event.group_id)
    else:
        gid = ""
    
    res, err = await pcrjjc.add_observer(cx, id, uid, gid)
    
    if err is not None:
        if isinstance(event, GroupMessageEvent):
            gid = str(event.group_id)
            err = f"[CQ:at,qq={uid}]{err}"
        await userQuery.send(err)
    else:
        if isinstance(event, GroupMessageEvent):
            gid = str(event.group_id)
            res = f"[CQ:at,qq={uid}]{res}"
            await bot.send_group_msg(group_id=gid, message=res)
        else:
            await bot.send_private_msg(user_id=uid, message=res) 
            
            
@delObserver.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    context = arg.extract_plain_text()
    pattern = re.compile(r'\s*(\d+)$')
    match = re.search(pattern, context)
    
    if match is not None:
        num = match.group(1)
        uid = str(event.user_id)
        res = pcrjjc.delete_observer(uid, num)
    else:
        
        res = "请输入要删除的序号"
    if isinstance(event, GroupMessageEvent):
        gid = str(event.group_id)
        res = f"[CQ:at,qq={uid}]{res}"
        await bot.send_group_msg(group_id=gid, message=res)
    else:
        await bot.send_private_msg(user_id=uid, message=res) 
            

@deleteGroup.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    if str(event.user_id) not in bot.config.superusers:
        return
    context = arg.extract_plain_text()
    pattern = re.compile(r'\s*(\d*)?$')
    match = re.search(pattern, context)
    
    if match is not None:
        gid = match.group(1)
        await pcrjjc.clear_group(gid)
        deleteGroup.finish('已删除该群的所有账号')

#------------------------------轮询任务-------------------------------#

async def callback(gid, uid, msg):
    global bot
    if gid != "":
        await bot.send_group_msg(
            group_id=int(gid),
            message=f'[CQ:at,qq={uid}]{msg}')
    else:
        bot.send_private_msg(
            user_id=uid, 
            message=msg)
        
        
@scheduler.scheduled_job(
    "interval",
    seconds=40,
)
async def __():
    global bot
    if bot is None:
        bot = get_bot()
    await pcrjjc.getAllInfo(callback)
   
#------------------------------配置相关-------------------------------#

@updatePCRVersion.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    if str(event.user_id) not in bot.config.superusers:
        return
    version = arg.extract_plain_text()
    msg = await pcrjjc.updateVersion(version)
    updatePCRVersion.finish(msg)