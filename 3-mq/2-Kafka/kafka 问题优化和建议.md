# kafka 问题优化和建议

> https://www.bilibili.com/video/BV1v7LP63EKe/?spm_id_from=333.1387.upload.video_card.click&vd_source=4e77ae7ca658e9a4c71fc3cc7a378962
>
> onedayhigh 2026-05-18 21:20:36

深夜某互联网公司的监控大屏突然爆红，KAFKA集群告警此起彼伏，手机推送一条接一条，值班工程师从梦中惊醒，一场线上风暴正在酝酿KAFKA问题，就这三层资源层，集群层，原数据层跟着风潮走，一层一层包，full gc就是世界暂停，ZOKEEPER收不到心跳，以为broker挂了堆，固定6G换G1，老年代到35%就开始并发标记，别等水杯满了才喝100兆的JSON，就像大象塞进油桶，page cash直接被碾碎，broker端max message biz等于一兆，producer端分片发送，别让一辆卡车堵死高速公路，broker被o m kill了，但别急着重启，先确认unclean leader election enable等于false，重启后先看i is2，同步确认数据追平，再宣告复活，leader像乒乓球一样来回跳，生产者不停重连，这是网络抖动的连锁反应，把lag超时调到60秒，ZK会话超时调到30秒，给系统多一点耐心，旧架构的controller是单线程排队，craft模式才能解开这把锁，unclean leader election enable等于false，意味着宁可停服也不丢数据，大V用户的key全哈希到一个分区，就像食堂一个窗口排长队迁移，用FTTO限速，就像给搬家车队发通行证，错峰出行，认证过了还得健全topic，写权限，group读权限缺一不可，Advertise listeners，配错客户端拿到的IP是内网的隔公网，当然连不上铁律全链路，UTC毫秒级时间戳，别让奈秒混进来。

重试三次后扔进DLQ死性topic，独立配TTL和监控，别让读完变成炸弹，记住这12字，GC停看堆0G1不行，换ZGC网络抖查DNS advertise，别写错，排查三字经GC停看堆零大消息做拆分，leader跳掉超时分区篇，重新算权限坑查ACL网络物，查DNS时间戳统一走死性毒射御值，三字经加思维导图，下次我照着查。



--- 由 vCaptions 生成 ---