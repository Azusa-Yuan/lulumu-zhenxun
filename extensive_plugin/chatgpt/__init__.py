import yaml
import os
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Message, GroupMessageEvent
from nonebot.params import CommandArg
from revChatGPT.V1 import Chatbot

cfgpath = os.path.join(os.path.dirname(__file__), 'config.yaml')
if os.path.exists(cfgpath):
    with open(cfgpath, 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)

chatbot = Chatbot(config=config)

__zx_plugin_name__ = "ChatGPT"
__plugin_usage__ = """
usage：
    #GPT + 问题
""".strip()
__plugin_des__ = "ChatGPT"
__plugin_cmd__ = ["GPT"]
__plugin_type__ = ("一些工具",)
__plugin_version__ = 0.1
__plugin_author__ = "Asuza_Yuan"

ai = on_command("#GPT", priority=5, block=True)


@ai.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not msg:
        return

    response = ""
    for data in chatbot.ask(msg):
        response = data["message"]

    await ai.send(response, at_sender=True)


