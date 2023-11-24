# -*- coding: utf-8 -*-

import os
import re
from urllib.parse import quote


notion_parts_re = re.compile(r"^# (.*?)\n\n([\s\S]*?)\n\n([\s\S]*)")
hugo_post_tpl = """
---
title: {title}
slug: {slug}
date: {date}
tags: {tags}
categories: {categories}
series: {series}
draft: false
---

{content}
"""


def list_posts_dir(base_path: str):
    """遍历文件夹下的所有包含文章的文件夹"""
    for item in os.listdir(base_path):
        full_path = os.path.join(base_path, item)
        if not os.path.isdir(full_path):
            continue
        # 判断子文件夹是否包含md文件
        is_post = False
        for sub_item in os.listdir(full_path):
            sub_full_path = os.path.join(full_path, sub_item)
            if not os.path.isfile(sub_full_path):
                continue
            if sub_item.endswith(".md"):
                is_post = True
        if not is_post:
            continue
        yield full_path


def list_post_file(base_path: str):
    """遍历文件夹下的所有md文件"""
    for item in list_posts_dir(base_path):
        for sub_item in os.listdir(item):
            sub_full_path = os.path.join(item, sub_item)
            if not os.path.isfile(sub_full_path):
                continue
            if sub_item.endswith(".md"):
                yield sub_full_path


def split_content(content: str):
    """将文章内容分割为元信息和正文"""
    matched = notion_parts_re.match(content)
    if not matched:
        raise Exception("文章格式错误")
    meta_content, title, body = matched.groups()
    return meta_content, title, body


def parse_post_tags(raw_tags: str) -> dict:
    """解析文章标签"""
    tags = dict(map(lambda x: x.split(": "), raw_tags.split("\n")))
    if "tags" in tags:
        tags["tags"] = tags.get("tags", "").split(", ")
    if "category" in tags:
        tags["category"] = tags.get("category", "").split(", ")

    return tags


def replace_post_content_image(post_file, slug, content: str) -> str:
    """替换文章中的图片"""
    basepath = os.path.dirname(post_file)
    # 获取图片文件夹
    pathname, ext = os.path.splitext(post_file)
    image_dir = os.path.basename(pathname)
    # 修改图片文件夹名称
    new_image_dir = os.path.join(basepath, slug)
    old_image_dir = os.path.join(basepath, image_dir)
    if os.path.exists(old_image_dir):
        os.rename(old_image_dir, new_image_dir)
    # 修改内容中的图片路径，需要先讲图片文件夹名称urlencode
    encode_image_dir = quote(image_dir)
    content = content.replace(f"{encode_image_dir}", f"{slug}")

    return content


def translate_post(post_file: str):
    with open(post_file) as f:
        content = f.read()
        title, raw_tags, post_content = split_content(content)
        print("start to process:", title)
        # 处理标签
        tags = parse_post_tags(raw_tags)
        # 处理图片
        slug = tags.get("slug", None)
        if not slug:
            raise Exception("文章slug不存在")
        post_content = replace_post_content_image(post_file, slug, post_content)
        hugo_psot_content = hugo_post_tpl.format(
            title=title,
            slug=tags.get("slug", ""),
            date=tags.get("date", ""),
            tags=tags.get("tags", []),
            categories=tags.get("category", []),
            series=tags.get("series", []),
            content=post_content,
        ).lstrip()
        # 写入文件
        basepath = os.path.dirname(post_file)
        new_post_file = os.path.join(basepath, f"{slug}.md")
        new_image_dir = os.path.join(basepath, slug)
        with open(new_post_file, "w") as f:
            f.write(hugo_psot_content)
        # 删除原文件
        os.remove(post_file)
        # TODO: 将文件移动到目标文件夹


def translate(base_path: str):
    # 读取文件
    pass
    #


if __name__ == "__main__":
    base_path = '/Users/zhengyansheng/Downloads/Notion2Hugo'
    base_path = "/Users/yaxin/Downloads/notion/"
    for item in list_post_file(base_path):
        translate_post(item)
