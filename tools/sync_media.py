# -*- coding: utf-8 -*-
"""将文章中的图片等下载到本地并且整理到规范的文件夹中
"""

import os
import re
import sys
import base64
from urllib.parse import unquote

import requests


image_re = re.compile(r"(!\[(.*?)\]\((.*?)\)[\n\r]+(图\s*\d+.*(?=\n)))", flags=re.MULTILINE)
image_desc_re = re.compile(r"^图(\d+)[.、：:\s]+(.*?)$")


def is_base64_image(content):
    """
    Check if the given content is a base64-encoded image.

    Args:
        content (str): The content to be checked.

    Returns:
        bool: True if the content is a base64-encoded image, False otherwise.
    """
    if content.startswith("data:image"):
        return True
    return False


def is_http_url(url):
    if url.startswith("http://") or url.startswith("https://"):
        return True
    return False

def get_base64_medsia_ext(content):
    """
    Get the file extension from a base64 media content.

    Parameters:
        content (str): The base64 media content.

    Returns:
        str: The file extension extracted from the content.
    """
    head = content[0:100]
    return head.split(";")[0].split("/")[1]


def copy_file(src, dest):
    """复制 src 文件到 dest"""
    with open(src, "rb") as f:
        content = f.read()
    with open(dest, "wb") as f:
        f.write(content)

def get_media_ext(file):
    """
    Get the file extension of a media file.

    Parameters:
        file (str): The file path or name.

    Returns:
        str: The file extension of the media file.
    """
    if is_base64_image(file):
        return get_base64_medsia_ext(file)
    media_ext = os.path.splitext(file)[1]

    return media_ext.strip(".")


def decode_base64_image(content: str):
    p = content.find("base64,")
    if p == -1:
        c = content
    else:
        c = content[p+7:]
    return base64.b64decode(c)


def download_file(url, local_path):
    """
    Downloads a file from the given URL and saves it to the local path.

    Parameters:
        url (str): The URL of the file to be downloaded.
        local_path (str): The local path where the file will be saved.

    Returns:
        bool: True if the file is successfully downloaded and saved, False otherwise.
    """
    # 已经下载的无需重复下载
    if os.path.exists(local_path):
        return True
    # 创建资源文件夹
    p = os.path.dirname(local_path)
    os.makedirs(p, exist_ok=True)

    # base64 编码的图片只要解码即可
    if is_base64_image(url):
        with open(local_path, "wb") as f:
            f.write(decode_base64_image(url))
        return True
    # 通过网络下载
    if is_http_url(url):
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
    # 本地文件只需要复制即可
    url = unquote(url)
    if os.path.exists(url):
        # 复制文件
        copy_file(url, local_path)
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


def tidy_up_media(post_file):
    """从给定的markdown格式文章中提取图片，下载后整理到规范的文件夹中"""
    pass

def get_media_url(image_url, post_file_dir):
    """
    Returns the media URL for a given image URL and post file directory.

    :param image_url: The URL of the image.
    :type image_url: str
    :param post_file_dir: The directory of the post file.
    :type post_file_dir: str
    :return: The media URL.
    :rtype: str
    """
    if is_http_url(image_url):
        return image_url
    if is_base64_image(image_url):
        return image_url
    return os.path.join(post_file_dir, image_url)


def main():
    """main"""
    if len(sys.argv) != 2:
        print("usage: {} <post_file>".format(sys.argv[0]))
        sys.exit(1)

    post_file = sys.argv[1]
    if not os.path.exists(post_file):
        print(f"post file {post_file} not exists")
        sys.exit(2)

    post_filepath = os.path.abspath(post_file)
    post_file_dir = os.path.dirname(post_filepath)
    post_filename = os.path.splitext(os.path.basename(post_filepath))[0]
    media_path = os.path.join(post_file_dir, post_filename)

    with open(post_filepath, "r", encoding="utf-8") as f:
        content = f.read()
        matched = image_re.findall(content)
        if matched:
            # 遍历图片
            for item in matched:
                raw_content = item[0]
                alt = item[1]
                image_url = item[2]
                title = item[3].replace("图 ", "图")
                # 将 title 翻译为英文
                media_name = translate(title)
                media_ext = get_media_ext(image_url)
                media_file = f"{media_name}.{media_ext}"
                image_url = get_media_url(image_url, post_file_dir)
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

if __name__ == "__main__":
    main()
