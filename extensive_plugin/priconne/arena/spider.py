import os
import re
import time
import json
import requests
from urllib.parse import urlparse, urlunparse
from requests.compat import quote, urljoin
from PIL import Image
from io import BytesIO
from configs.path_config import IMAGE_PATH
nowpath = os.path.abspath(os.path.join(IMAGE_PATH, 'priconne/'))
imgNameList = []
import aiohttp
# pycharm写法
# import sys
# sys.path.append("..")
# import _pcr_data
from .. import _pcr_data
# for single_dir in picture_list:
#     name = int(re.findall(r"\d+",single_dir)[0])
#     imgNameList.append(name)


class Spider(object):

    def download_img(self, save_path, link):
        # print('download_img from ', link, end=' ')
        # 改成携程下载的事暂时搁置
        resp = requests.get(link, stream=True)
        # print('status_code=', resp.status_code, end=' ')
        if 200 == resp.status_code:
            if re.search(r'image', resp.headers['content-type'], re.I):
                print(f'is image, saving to {save_path}', end=' ')
                img = Image.open(BytesIO(resp.content))
                img.save(save_path)
                return True

    def download_icon_unit(self):
        value_list = list(_pcr_data.CHARA_NAME.keys())
        msg = ''
        base = 'https://redive.estertion.win/icon/unit/'
        save_dir = os.path.join(nowpath, './unit/')
        picture_list = os.listdir(save_dir)
        os.makedirs(save_dir, exist_ok=True)

        def get_pic_name(pic_id, pre, end):
            return f'{pre}{pic_id:0>4d}{end}'
        stars = [1, 3, 6]
        for i in value_list:
            for star in stars:
                src_n = get_pic_name(i, '', f'{star}1.webp')
                dst_n = get_pic_name(i, 'icon_unit_', f'{star}1.png')
                if dst_n in picture_list:
                    #print('存在')
                    continue
                flag = self.download_img(os.path.join(save_dir, dst_n), urljoin(base, src_n))
                if flag:
                    if msg:
                        msg += '\n' + get_pic_name(i, '', f'{star}1') + '下载成功'
                    else:
                        msg += get_pic_name(i, '', f'{star}1') + '下载成功'
                    time.sleep(0.2)
        return msg

    def download_comic(self, start=1, end=200, only_index=False):
        base = 'https://comic.priconne-redive.jp/api/detail/'
        save_dir = './comic/'
        os.makedirs(save_dir, exist_ok=True)

        def get_pic_name(id_):
            pre = 'episode_'
            end = '.png'
            return f'{pre}{id_}{end}'

        index = {}

        for i in range(start, end):
            print('getting comic', i, '...', end=' ')
            url = base + str(i)
            print('url=', url, end=' ')
            resp = requests.get(url)
            print('status_code=', resp.status_code)
            if 200 != resp.status_code:
                continue
            data = resp.json()[0]

            # if data['current_index'] != False:
            episode = data['episode_num']
            title = data['title']
            link = data['cartoon']
            index[episode] = {'title': title, 'link': link}
            print(index[episode])
            if not only_index:
                self.download_img(os.path.join(save_dir, get_pic_name(episode)), link)
            time.sleep(0.1)
            print('\n', end='')
            # else:
            #     print('current_index not True, ignore')

        with open(os.path.join(save_dir, 'index.json'), 'w', encoding='utf8') as f:
            json.dump(index, f, ensure_ascii=False)


if __name__ == '__main__':
    spider = Spider()
    spider.download_icon_unit(start=1000, end=1238, star=1)
    spider.download_icon_unit(start=1000, end=1238, star=3)
    spider.download_icon_unit(start=1000, end=1238, star=6)
    #spider.download_comic(start=1, end=198, only_index=True)
