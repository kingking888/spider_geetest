# -*-coding:utf-8 -*-
import time
import random
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from bs4 import BeautifulSoup
from urllib.request import urlretrieve
import cons
import json
import urllib.request
import mysql_conn as mc
import pandas as pd
from jsw_get_log import jsw_get_log


class Crack(object):
    def __init__(self):
        self.url = cons.index_url
        self.browser = webdriver.Chrome(executable_path=cons.chromedriver_path)
        self.wait = WebDriverWait(self.browser, cons.timeout)
        self.border = cons.border

    def get_slider(self):
        """
        获取滑块
        :return: 滑块对象
        """
        slider = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, cons.slider_class_name)))
        return slider

    def open(self):
        """
        打开浏览器,并输入查询内容
        """
        self.browser.get(self.url)
        login_button = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, cons.login_button)))
        login_button.click()
        slider = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'gt_slider_knob')))
        slider.click()

    def get_images(self, bg_filename=cons.bg_filename, full_bg_filename=cons.full_bg_filename):
        """
        获取验证码图片
        :return: 图片的location信息
        """
        bg = []
        full_bg = []
        while bg == [] and full_bg == []:
            bf = BeautifulSoup(self.browser.page_source, 'lxml')
            bg = bf.find_all('div', class_=cons.bg_class)
            full_bg = bf.find_all('div', class_=cons.full_bg_class)
        bg_url = re.findall(cons.bg_url_re, bg[0].get('style'))[0].replace('webp', 'jpg')
        full_bg_url = re.findall(cons.full_bg_url_re, full_bg[0].get('style'))[0].replace('webp', 'jpg')
        bg_location_list = []
        full_bg_location_list = []
        for each_bg in bg:
            location = dict()
            location['x'] = int(re.findall(cons.bg_location_re_x, each_bg.get('style'))[0][0])
            location['y'] = int(re.findall(cons.bg_location_re_y, each_bg.get('style'))[0][1])
            bg_location_list.append(location)
        for each_full_bg in full_bg:
            location = dict()
            location['x'] = int(re.findall(cons.full_bg_location_re_x, each_full_bg.get('style'))[0][0])
            location['y'] = int(re.findall(cons.full_bg_location_re_y, each_full_bg.get('style'))[0][1])
            full_bg_location_list.append(location)
        urlretrieve(url=bg_url, filename=bg_filename)
        urlretrieve(url=full_bg_url, filename=full_bg_filename)
        return bg_location_list, full_bg_location_list

    @staticmethod
    def get_merge_image(filename, location_list):
        """
        根据位置对图片进行合并还原
        :filename:图片
        :location_list:图片位置
        """
        im = Image.open(filename)
        Image.new('RGB', (260, 116))
        im_list_upper = []
        im_list_down = []
        for location in location_list:
            if location['y'] == -58:
                im_list_upper.append(im.crop((abs(location['x']), 58, abs(location['x']) + 10, 166)))
            if location['y'] == 0:
                im_list_down.append(im.crop((abs(location['x']), 0, abs(location['x']) + 10, 58)))
        new_im = Image.new('RGB', (260, 116))
        x_offset = 0
        for im in im_list_upper:
            new_im.paste(im, (x_offset, 0))
            x_offset += im.size[0]
        x_offset = 0
        for im in im_list_down:
            new_im.paste(im, (x_offset, 58))
            x_offset += im.size[0]
        new_im.save(filename)
        return new_im

    def get_gap(self, img1, img2):
        """
        获取缺口偏移量
        :param img1: 不带缺口图片
        :param img2: 带缺口图片
        :return:
        """
        left = cons.get_gap_left
        for i in range(left, img1.size[0]):
            for j in range(img1.size[1]):
                if not self.is_pixel_equal(img1, img2, i, j):
                    left = i
                    return left
        return left

    @staticmethod
    def is_pixel_equal(img1, img2, x, y):
        """
        判断两个像素是否相同
        :param img1: 图片1
        :param img2: 图片2
        :param x: 位置x
        :param y: 位置y
        :return: 像素是否相同
        """
        # 取两个图片的像素点
        pix1 = img1.load()[x, y]
        pix2 = img2.load()[x, y]
        threshold = cons.is_pixel_equal_threshold

        if (abs(pix1[0] - pix2[0] < threshold) and abs(pix1[1] - pix2[1] < threshold) and abs(
                pix1[2] - pix2[2] < threshold)):
            return True
        else:
            return False

    @staticmethod
    def get_track(distance):
        """
        根据偏移量获取移动轨迹
        geetest插件会拒绝瞬间移动或者匀速直线运动等，因此要模拟人的运动，先快后慢
        :param distance: 偏移量
        :return: 移动轨迹
        """
        # 移动轨迹
        track = []
        # 当前位移
        current = 0
        # 减速阈值
        mid = distance * 4 / 5
        # 计算间隔
        t = 0.2
        # 初速度
        v0 = 0

        while current < distance:
            if current < mid:
                # 加速度为正2
                a = 4
            else:
                # 加速度为负3
                a = -3.5
            # 移动距离x = v0t + 1/2 * a * t^2
            move = v0 * t + 1 / 2 * a * t * t
            # 当前速度v = v0 + at
            v = v0 + a * t
            # 初速度v0
            v0 = v
            # 当前位移
            current += move
            # 加入轨迹
            track.append(round(move))
        return track

    def move_to_gap(self, slider, track):
        """
        拖动滑块到缺口处
        :param slider: 滑块
        :param track: 轨迹
        :return:
        """
        time.sleep(2)
        ActionChains(self.browser).click_and_hold(slider).perform()

        for i in track:
            ActionChains(self.browser).move_by_offset(xoffset=i, yoffset=0).perform()

        imitate = ActionChains(self.browser).move_by_offset(xoffset=-1, yoffset=0)
        time.sleep(0.015)
        imitate.perform()
        time.sleep(random.randint(6, 10) / 10)
        imitate.perform()
        time.sleep(0.04)
        imitate.perform()
        time.sleep(0.012)
        imitate.perform()
        time.sleep(0.019)
        imitate.perform()
        time.sleep(0.033)
        ActionChains(self.browser).move_by_offset(xoffset=1, yoffset=0).perform()
        ActionChains(self.browser).pause(random.randint(6, 14) / 10).release(slider).perform()

    def login(self):
        """
        模拟登录，得到cookie
        :return: 成功返回cookie，失败返回false
        """
        time.sleep(5)
        name_input = self.wait.until(EC.presence_of_element_located((By.ID, cons.login_name_input_id)))
        pwd_input = self.wait.until(EC.presence_of_element_located((By.ID, cons.login_pwd_input_id)))
        name_input.send_keys(cons.login_username)
        pwd_input.send_keys(cons.login_pwd)
        login_button = self.wait.until(EC.presence_of_element_located((By.ID, cons.login_login_button_id)))
        login_button.click()
        time.sleep(2)
        cookie_list = self.browser.get_cookies()
        cookie = ''
        for i in cookie_list:
            cookie += "%s=%s; " % (i['name'], i['value'])
        if "tgbpwd" in cookie and "tgbuser" in cookie:
            return cookie
        else:
            return False

    def crack(self):
        # 打开浏览器
        self.open()
        # 获取图片
        bg_filename = cons.bg_filename
        full_bg_filename = cons.full_bg_filename
        bg_location_list, full_bg_location_list = self.get_images(bg_filename, full_bg_filename)
        # 根据位置对图片进行合并还原
        bg_img = self.get_merge_image(bg_filename, bg_location_list)
        full_bg_img = self.get_merge_image(full_bg_filename, full_bg_location_list)
        # 获取缺口位置
        gap = self.get_gap(full_bg_img, bg_img)
        track = self.get_track(gap - self.border)
        # 获取滑块对象
        slider = self.get_slider()
        # 拖动滑块到缺口处
        self.move_to_gap(slider, track)
        # 模拟登陆
        res = self.login()

        self.browser.close()
        return res


def taoguba_spider(cookie):
    delay = 0
    while True:
        try:
            url = "https://www.taoguba.com.cn/spmatch/getAllSpMatchPage?pageNo=1&type=2&orderByType=nowUserNum&order=D"
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req)
            html_Str = response.read().decode("utf-8")
            value_list = re.findall('<td><span class="readBtn" value="(.*?)" subject=', html_Str, re.S)[0:10]
            url_pool = []
            for i in value_list:
                i = i.replace(" ", "")
                url = 'https://www.taoguba.com.cn/spmatch/buyLongHuBang?spMatchSeq=' + '%s' % i + '%20&longHuType=M'
                url_pool.append(url)

            dict1 = {}
            list1 = []
            list2 = []
            list3 = []
            headers = {"User-Agent": "User-Agent, Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11"
                                     " (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
                       "Cookie": cookie
                       }
            for url in url_pool:
                req = urllib.request.Request(url, headers=headers)
                response = urllib.request.urlopen(req, timeout=100)
                html_str = response.read()
                json_data = json.loads(html_str)
                for n in ["buySpLists", "postSplists", "saleSplists"]:
                    for i in range(10):
                        list4 = []
                        try:
                            number = json_data["dto"][n][i]["stockCode"][2:]
                            name = json_data["dto"][n][i]["stockName"]
                            count = json_data["dto"][n][i]["countNum"]
                            if not name:
                                name = "无"
                        except IndexError:
                            number = "000000"
                            name = "无"
                            count = "0"
                        list4.append(number)
                        list4.append(name)
                        list4.append(count)
                        if n == "buySpLists":
                            type1 = "买入排行"
                            b = False
                            for j in range(len(list1)):
                                if list1[j][0] == list4[0]:
                                    list1[j][2] = str(int(list1[j][2]) + int(list4[2]))
                                    b = True
                            if not b:
                                list1.append(list4)
                            dict1[type1] = list1
                        elif n == "postSplists":
                            type1 = "持仓排行"
                            b = False
                            for j in range(len(list2)):
                                if list2[j][0] == list4[0]:
                                    list2[j][2] = str(int(list2[j][2]) + int(list4[2]))
                                    b = True
                            if not b:
                                list2.append(list4)
                            dict1[type1] = list2
                        else:
                            type1 = "卖出排行"
                            b = False
                            for j in range(len(list3)):
                                if list3[j][0] == list4[0]:
                                    list3[j][2] = str(int(list3[j][2]) + int(list4[2]))
                                    b = True
                            if not b:
                                list3.append(list4)
                            dict1[type1] = list3
                time.sleep(60)
            engine = mc.get_local_engine("stockhot")
            df = pd.DataFrame()
            datatime = time.strftime('%F %H:%M')
            data = time.strftime('%F')
            for type1 in ["买入排行", "持仓排行", "卖出排行"]:
                for i in range(len(dict1[type1])):
                    df.loc[i, "code"] = dict1[type1][i][0]
                    df.loc[i, "name"] = dict1[type1][i][1]
                    df.loc[i, "count"] = dict1[type1][i][2]
                    df.loc[i, "datetime"] = datatime
                    df.loc[i, "type"] = type1
                    df.loc[i, "data"] = data
                engine.update_df(df, "hotstocks")
            return "success"
        except Exception as e:
            time.sleep(1200)
            delay += 1
            if delay == 3:
                return e


if __name__ == '__main__':
    logger = jsw_get_log("stockhot")
    result = False
    num = 0
    while (not result) and (num < 8):
        crack = Crack()
        result = crack.crack()
        num += 1
        time.sleep(5)
    if result:
        logger.info(taoguba_spider(result))
    else:
        logger.info("login_error")
