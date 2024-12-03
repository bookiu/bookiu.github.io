---
title: "TSO 对延迟的影响"
slug: how-tso-affect-latency
description: "TSO 对延迟的影响"
date: 2024-12-03T10:34:50+08:00
tags: ["网络"]
category: ["网络"]
series: []
image: ""
draft: false
---

最近将生产环境所有服务器（某云上）的 TSO 特性全部关闭，收获了近 10ms 延迟的优化和约 0.01% 成功率的提升。这个收益是超预期的，本文也尝试记录分析一下此收益的根因，及在什么情况下推荐关闭 TSO 特性。

## 0x01 什么是 TSO

`TSO` 全称 `TCP segmentation offload`，是一种通过将大包分割逻辑转移到网卡，从而降低 CPU 负载的技术。我们下面通过发包流程图来深入讲解一下。

### 1.1 未开启 TSO 发包流程

![图1、未开启 TSO 发包流程](https://r2.kdefan.net/blog/2024/12/01_未开启_TSO_发包流程.png)

在未开启 TSO 的情况下，应用程序调用 `send` 接口向外发送数据，会途径系统内核，再到网卡，然后通过网线、交换机等到达对端。这里有一种情况，假如 `send` 发送的数据比较大，超过了 MTU（**M**aximum **T**ransmission **U**nit），那系统内核会将数据包拆分为多个小包再发给网卡。

例如，应用程序发送了一个 64 KiB (65,536 bytes) 的数据，系统内核会其分为 45 个 1460 bytes 的数据包发给网卡。这就带来一个问题，系统内核承担了分包的逻辑，导致 CPU 负载的上涨。为了解决/优化这个问题，网卡支持了 TSO 特性。

### 1.2 开启 TSO 发包流程

![图2、开启 TSO 后发包流程](https://r2.kdefan.net/blog/2024/12/02_开启_TSO_后发包流程.png)

开启 TSO 特性后，如果数据比较大，系统内核也不做分包处理，而是直接将数据包转给网卡，网卡再将数据根据 MTU 设置拆分为多个小包。这样，通过将分包逻辑转移到网卡等硬件设备，降低 CPU 负载。

## 0x02 TSO 对延迟的影响

TSO 的出发点是好的，通过将分包逻辑转移，实现 CPU 负载的降低。但这带来了一个新的问题：少量丢包会引起整个大包的重传。

TCP 本身有滑动窗口确认机制，在开启 TSO 的情况下，滑动窗口记录的是大包的长度，期望收到的也是大包的 ACK 确认值。但如果此时网络质量下降导致网卡拆分的小包中的任何一个包丢失、错误等，会导致整个大包重传。多数情况下丢包等一般都是链路中网络设备压力过大，而整个大包的重传则进一步加重网络负载从而导致更多丢包的产生。

## 0x03 实际效果

事情的起因是生产环境的某个组件延迟频繁出现延迟抖动，导致接口整体延迟不稳定，且失败率升高。

![图3、延迟异常抖动](https://r2.kdefan.net/blog/2024/12/03_延迟异常抖动.png)

按照我们在其它环境的一个排查经验（另外一个故事，有时间整理出来），关闭 TSO 有较大概率缓解、消除这种抖动，于是我们尝试对数据中心所有服务器关闭 TSO 特性。

关闭是分批进行的，主要防止有副作用（理论上不会有），随着关闭数量的增加，延迟也是断崖式下跌，这个本身是超过我们预期的。最后在关闭所有离线（我们的离线 yarn、hdfs 等）机器的 TSO 特性后，延迟降到了最低。

![图4、灰度过程中延迟对比](https://r2.kdefan.net/blog/2024/12/04_灰度过程中延迟对比.png)

相应的大部分组件的 TCP 包重传率也有较大幅度的下降。

![图5、重传率下降](https://r2.kdefan.net/blog/2024/12/05_重传率下降.png)

### 3.1 副作用

关闭并 TSO 并不全是收益，也会产生一些「副作用」，首当其冲的就是 CPU 负载有小幅上涨，这个是符合预期（这也是 TSO 产生的原因之一：降低 CPU 压力），但是这点上涨对于当下 CPU 性能和配置来说不值一提。

![图6、CPU 负载略微升高](https://r2.kdefan.net/blog/2024/12/06_CPU_负载略微升高.png)

另一个副作用就是出网卡的数据包会有较大增长（看业务特性，有些增长不明显），这给交换机带来一定的压力，需要评估上联交换机是否可以承受如此大的 pps（Packets Per Second）。

![图7、PPS 显著升高](https://r2.kdefan.net/blog/2024/12/07_PPS_显著升高.png)

## 0x04 总结

TSO 的出现是为了优化高带宽下包拆分对 CPU 造成的压力，但同时也带来了一定的副作用。如果你当前的**网络压力比较大，质量也比较差**（重传率比较高），可以尝试关闭 TSO 特性来尝试优化。

关闭 TSO 需要使用 `ethtool` 工具，并且由于 TSO 是网卡特性，因此需要判断网卡是否是物理网卡，整理后的脚本如下：

```bash
log_info() {
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)][INFO] $*"
}

for dev in $(ip -o link show | awk -F':' '{print $2}'); do
    # check dev is physical interface
    if [[ ! -e "/sys/class/net/${dev}/device" ]]; then
        log_info "device is not physical interface, skip. device=${dev}"
        continue
    fi
    log_info "start to close device tso. device=${dev}"

    ethtool -K ${dev} tso off

    log_info "close device tso success. device=${dev}"

    res=$(ethtool -k ${dev} 2> /dev/null | grep 'tcp-segmentation-offload')
    log_info "check device tso is closed. device=${dev} res=${res}"
done
```
