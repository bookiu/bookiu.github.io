# -*- coding: utf-8 -*-

import os
import re

import requests


root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
posts_path = os.path.join(root_path, "content", "posts")

image_re = re.compile(r"(!\[(.*?)\]\((.*?)\)[\n\r]+(图\d+.*(?=\n)))", flags=re.MULTILINE)
image_desc_re = re.compile(r"^图(\d+)[.、：:\s]+(.*?)$")


def download_file(url, local_path):
    """下载文件"""
    if os.path.exists(local_path):
        return True
    p = os.path.dirname(local_path)
    os.makedirs(p, exist_ok=True)

    r = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/90.0.4430.212 Safari/537.36"
    }, stream=True)
    if r.status_code == 200:
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                f.write(chunk)
        return True
    return False

def translate(text):
    """翻译"""
    c = text.strip()
    # 将其中的连续空格替换为_
    c = re.sub(r"\s+", "_", c)
    matched = image_desc_re.findall(c)
    if not matched:
        return text
    number = matched[0][0]
    desc = matched[0][1]
    if desc.endswith("。"):
        desc = desc[:-1]
    prefix = str(number).rjust(2, '0')
    return f"{prefix}_{desc}"

post_file = "what-is-glue-records.md"
post_filepath = os.path.join(posts_path, post_file)
post_filename = os.path.splitext(post_file)[0]
media_path = os.path.join(posts_path, post_filename)

with open(post_filepath, "r", encoding="utf-8") as f:
    content = f.read()
    matched = image_re.findall(content)
    if matched:
        for item in matched:
            raw_content = item[0]
            alt = item[1]
            image_url = item[2]
            title = item[3]
            # 将 title 翻译为英文
            media_name = translate(title)
            media_ext = os.path.splitext(image_url)[1]
            media_file = f"{media_name}{media_ext}"
            # 下载图片
            download_file(image_url, os.path.join(media_path, f"{media_file}"))
            # 替换内容
            pic_with_title = f"![{title}](./{post_filename}/{media_file})"
            if raw_content.endswith("\n"):
                pic_with_title += "\n"
            content = content.replace(raw_content, pic_with_title)

with open(post_filepath, "w", encoding="utf-8") as f:
    # 回写文件
    f.write(content)
