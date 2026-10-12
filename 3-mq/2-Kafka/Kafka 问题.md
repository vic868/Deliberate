# Kafka 问题

> https://www.bilibili.com/video/BV1PLLA69Eit/?spm_id_from=333.1387.upload.video_card.click&vd_source=4e77ae7ca658e9a4c71fc3cc7a378962
>
> onedayhigh 2026-05-18 16:13:22

00:00 老马老马你在吗，
00:02 618大醋缸上线半小时，
00:04 系统疯了，
00:06 别慌，
00:07 截图给我看看，
00:08 我看到了不止一个问题，
00:11 我数了一下，
00:12 至少七个地方在着火，
00:15 七个我就改了个batch size撒，
00:19 别急，
00:20 一个个来，
00:21 先从最紧急的开始吞吐瓶颈，
00:24 这不就是堵车吗，
00:26 消息全堵在路上了，
00:29 没错你的producer每秒扔5000条消息进来，
00:32 但consumer每秒只处理200条，
00:35 batch size默认才16KB，
00:38 就像搬家用购物袋装东西调到256KB，
00:41 一次装更多吞吐直接翻倍，
00:45 linger ms呢让他等20ms凑批，
00:50 配合batch size双剑合璧，
00:53 consumer数量要跟partition数匹配，
00:55 你三个partition却只跑了一个consumer啊，
01:01 我加了三个consumer了，
01:03 怎么还是很慢，
01:05 看一下partition分布，
01:07 数据倾斜了一个partition，
01:09 堵死其他两个闲着，
01:11 fetch man BIS默认一字节改成64KB，
01:14 让broker团购数据再返回，
01:18 明白了，
01:18 就像搬家一次，
01:20 多搬几个箱子，
01:21 少跑几趟，
01:22 磁盘告警了，
01:23 有一块盘使用率快100%了，
01:27 数据倾斜导致的热点问题，
01:29 给消息T1加随机后缀，
01:31 让消息均匀散到不同分区，
01:34 订单怎么会凭空消失，
01:36 我明明发了你producer的ex配的几零，
01:43 我看文档说零是最快的最快，
01:47 但最危险线上环境必须X等于all i is2收缩，
01:52 如果i is2里只剩leader一个，
01:55 Mean in in sync replicas，
01:57 配的又是1leader1挂，
02:00 然后选了一个数据严重落后的follower，
02:03 当leader没错，
02:06 Unclean leader election。

02:08 线上一定要unclean leader election，
02:11 enable等于false，
02:12 开启enable，
02:14 IDENTENCE等于true，
02:15 每条消息待序列号，
02:17 broker收到重复的直接丢弃，
02:20 那producer崩溃，
02:22 重启序列号会重置吗，
02:25 pad会变，
02:26 所以me等指在单次会话内有效跨会画，
02:29 需要事务客户投诉说被扣了两次钱，
02:33 同一条订单消息被处理了两遍，
02:37 经典的at least once语义，
02:39 consumer处理完蛋，
02:40 还没提交offset就被REBALANCE掉了，
02:43 cf cat事务API把处理消息加提交offset，
02:47 绑定成一个原子操作，
02:50 就像转账要么都成功，
02:52 要么都失败，
02:54 完全正确，
02:56 消息乱序的根本原因是发送端并发太多，
03:01 对max in flight requests，
03:03 Poor connection，
03:05 控制了在图请求数，
03:06 开启密等加限制飞行数顺序和唯一性就稳了，
03:10 consumer一直在重新读之前读过的消息，
03:13 死循环了，
03:16 offset丢了，
03:17 Auto offset，
03:19 reset等于earliest，
03:20 就从头读，
03:21 自动提交，
03:22 就像定时闹钟，
03:23 每五秒响一次，
03:25 不管你消息有没有处理完，
03:28 所以线上要用手动提交，
03:31 处理完一批再提交，
03:33 确保不丢不中，
03:34 offset下划线，
03:36 out下划线，
03:37 OF下划线range，
03:38 这是什么鬼，
03:40 consumer想消费的offset在topic里不存在，
03:44 最简单修复是重置offset，
03:46 earliest或latest broker，
03:48 零挂了数据不会丢吧，
03:52 看你replication factor设的几，
03:54 三的话有三副本，
03:56 leader选举会自动切换，
03:58 有个broker挂了，
04:00 日志显示NO space left on device，
04:04 磁盘满了，
04:05 cf cat是日志型存储。

04:07 全靠清理策略，
04:08 Log retention，
04:10 bias和log retention ours都要配，
04:13 刚才集群有一个瞬间完全不可用，
04:17 controller宕机后选举这段时间集群处于脑裂状态，
04:21 用craft模式替代ZOKEEPER能更快恢复，
04:24 consumer一直在重启日志里疯狂打REBALANCE，
04:28 到底什么是REBALANCE，
04:31 consumer group成员变化时，
04:33 所有partition重新分配，
04:35 分配期间消费完全停止，
04:37 这不就是死亡螺旋吗，
04:39 一轮接一轮越来越惨，
04:42 开启增量式协作重平衡，
04:44 Partition assignment，
04:46 strategy等于cooperative sticky，
04:48 消费者一个一个退，
04:49 不用全组停，
04:50 Sticky signore，
04:52 尽量保持原有分配不变，
04:53 静态成员让consumer短暂离线，
04:55 不触发REBALANCE，
04:57 调大超时参数，
04:58 给足喘息空间，
04:59 三件套以上，
05:00 REBALANCE频率从每小时几十次降到几乎为零，
05:04 七个问题全解决了，
05:07 你来总结，
05:10 吞吐靠批量化，
05:12 不丢消息，
05:12 靠X等于or不重复，
05:14 靠事物不乱序，
05:15 靠key哈希offset安全靠手动提交，
05:18 集群稳定靠冗余，
05:20 REBALANCE可控，
05:21 靠static membership，
05:22 这六条不是圣经，
05:24 是血淋淋的工单堆出来的，
05:25 检查清单，
05:26 每次上线前过一遍，
05:28 能避开90%的KAFKA，
05:30 深夜告警，
05:32 记下来了，
05:33 你看lag归零了，
05:35 天也亮了，
05:37 KAFKA这头野兽驯服了，
05:39 就是最强消息管道。



--- 由 vCaptions 生成 ---