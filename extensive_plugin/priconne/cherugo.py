from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message
import re
from itertools import zip_longest
import os
from .textfilter.filter import DFAFilter
from nonebot.params import CommandArg


__zx_plugin_name__ = "切噜一下"

__plugin_usage__ = """
usage：
    [切噜一下] 转换为切噜语
    [切噜～♪切啰巴切拉切蹦切蹦] 切噜语翻译
""".strip()
__plugin_des__ = "切噜一下"
__plugin_cmd__ = [
    "切噜一下",
    "切噜～♪切啰巴切拉切蹦切蹦",
]
__plugin_type__ = ("PCR相关", )
__plugin_version__ = 0.1


CHERU_SET = '切卟叮咧哔唎啪啰啵嘭噜噼巴拉蹦铃'
CHERU_DIC = {c: i for i, c in enumerate(CHERU_SET)}
ENCODING = 'gb18030'
rex_split = re.compile(r'\b', re.U)
rex_word = re.compile(r'^\w+$', re.U)
rex_cheru_word: re.Pattern = re.compile(rf'切[{CHERU_SET}]+', re.U)

gfw = DFAFilter()
gfw.parse(os.path.join(os.path.dirname(__file__), 'textfilter/sensitive_words.txt'))


def filt_message(message: str):
    if isinstance(message, str):
        return gfw.filter(message)
    elif isinstance(message, Message):
        for seg in message:
            if seg.type == 'text':
                seg.data['text'] = gfw.filter(seg.data.get('text', ''))
        return message
    else:
        raise TypeError

def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def word2cheru(w: str) -> str:
    c = ['切']
    for b in w.encode(ENCODING):
        c.append(CHERU_SET[b & 0xf])
        c.append(CHERU_SET[(b >> 4) & 0xf])
    return ''.join(c)


def cheru2word(c: str) -> str:
    if not c[0] == '切' or len(c) < 2:
        return c
    b = []
    for b1, b2 in grouper(c[1:], 2, '切'):
        x = CHERU_DIC.get(b2, 0)
        x = x << 4 | CHERU_DIC.get(b1, 0)
        b.append(x)
    return bytes(b).decode(ENCODING, 'replace')


def str2cheru(s: str) -> str:
    c = []
    for w in rex_split.split(s):
        if rex_word.search(w):
            w = word2cheru(w)
        c.append(w)
    return ''.join(c)


def cheru2str(c: str) -> str:
    return rex_cheru_word.sub(lambda w: cheru2word(w.group()), c)


cherulize = on_command("切噜一下",  block=True, priority=5)
decherulize = on_command("切噜～♪",  block=True, priority=5)


@cherulize.handle()
async def cherulize_handle(bot,event: MessageEvent, arg: Message = CommandArg()):
    s = arg.extract_plain_text()
    if len(s) > 500:
        await cherulize.finish('切、切噜太长切不动勒切噜噜...')
        return
    await cherulize.finish('切噜～♪' + str2cheru(s), at_sender=True)


@decherulize.handle()
async def decherulize_handle(bot,event: MessageEvent, arg: Message = CommandArg()):
    s = arg.extract_plain_text()
    if len(s) > 1501:
        await decherulize.finish('切、切噜太长切不动勒切噜噜...')
        return
    msg = '你的切噜噜是：\n' + filt_message(cheru2str(s))
    await decherulize.finish(msg, at_sender=True)
