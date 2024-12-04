---
title: Linux下检测端口是否打开
slug: linux-port-open-check
aliases:
    - /posts/linux-port-open-check
date: 2021-01-06T11:50:00+08:00
tags: ['linux', 'wireshark']
categories: ['网络']
series: []
draft: false
---

排查网络故障的时候我们常用的一个方法就是探测一下远端端口是否可以连接，而一个好的探测工具能为我们节省很多时间，下面我就分享一些常用的端口检测的工具。

## 0x01 telnet

`telnet`是一个经典的telnet协议的客户端，因为`telnet`协议是一个基于tcp的文本协议，因此我们可以用它来探测端口是否开放，其命令如下

```bash
# telnet 域名或IP 端口
telnet 12.1.1.1 22
```

端口通的情况：

![端口开放的情况](linux-port-open-check/Untitled.png)

端口开放的情况

端口不通的情况：

![端口不通的情况](linux-port-open-check/Untitled%201.png)

端口不通的情况

![linux-port-open-check/Untitled%202.png](linux-port-open-check/Untitled%202.png)

## 0x02 nc

`nc`命令全称netcat，是网络调试中瑞士军刀级别的工具，它的作用包括但不限于：

1. 搭建简单的HTTP服务，或作为客户端
2. 搭建TCP服务
3. 配合ssh中的ProxyCommand使用
4. 网络检测

我们这里主要使用他的网络检测的能力，其简单的检测命令为：

```bash
# nc -v 域名或IP 端口
nc -v qq.com 80
```

`nc`命令会显式的打印出成功的情况，对于端口不通，nc和可能会阻塞很久也可能直接返回失败。

端口通的情况：

![端口打开的情况](linux-port-open-check/Untitled%203.png)

端口打开的情况

端口不通的情况：

![端口不通的情况](linux-port-open-check/Untitled%204.png)

端口不通的情况

![linux-port-open-check/Untitled%205.png](linux-port-open-check/Untitled%205.png)

## 0x03 bash特殊设备文件

bash下存在一个特殊的设备文件：**/dev/(tcp|udp)/<HOST>/<PORT>**，打开该文件，就相当于建立了一个socket连接，读写这个文件就相当于在socket中传输数据。基于这个特性，我们可以用来做端口开放性检测，调用方式如下：

```bash
echo > /dev/tcp/qq.com/80
```

端口通的情况下：

![linux-port-open-check/Untitled%206.png](linux-port-open-check/Untitled%206.png)

端口不通的情况下：

![linux-port-open-check/Untitled%207.png](linux-port-open-check/Untitled%207.png)

![linux-port-open-check/Untitled%208.png](linux-port-open-check/Untitled%208.png)

## 0x04 端口不通为什么会出现阻塞

最后我们解释一下端口不通的情况下为什么会出现长时间阻塞，其实这个很好解释：客户端在等服务器端返回数据包，正常情况下，如果端口未开放，服务端会直接返回一个`RST`包，客户端收到这个包后会直接关闭`socket`然后返回退出，但如果服务端配置了防火墙（iptables），直接把未开放端口的请求包丢弃，那客户端就永远不可能收到回报，但客户端又不知道包被丢弃了，于是就傻傻重传然后继续等，直到超时。我们通过`tcpdump`抓包看一下：

![linux-port-open-check/Untitled%209.png](linux-port-open-check/Untitled%209.png)

上图显示的端口通的情况，可以清晰的看到TCP三次握手四次挥手。

![linux-port-open-check/Untitled%2010.png](linux-port-open-check/Untitled%2010.png)

上图显示了端口不通，但防火墙丢包的情况，可以看到，客户端一直在傻傻的重传`syn`包。

![linux-port-open-check/Untitled%2011.png](linux-port-open-check/Untitled%2011.png)

上图是端口不通，且没有防火墙丢包等情况，可以看到服务端直接返回了`rst`包。
