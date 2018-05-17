# Pwn方向出题模板

## 基本要求
* 实现能通过`test.client.py`检查的服务程序，确保基本功能完整（服务程序python实现示例`service_example.py`）；
* 必须包含安全漏洞，不限漏洞类型；
* C/C++语言实现，提供源码和编译环境，编译运行在x86、ARM或MIPS架构上；
* 赛题环境提供Dockerfile + docker-compose容器环境，主办方使用`docker-compose up -d`启动选手提供的环境（docker环境内初始**只包含源码, 不要预编译二进制**，编译命令和运行命令写入Dockerfile，由Docker自动编译和运行）；
* 服务端口统一为`1337`，请不要使用其他端口。
* Flag可即时更新，不接受固定flag的赛题。请在文档内提供更新flag的命令，例如`echo xxx > /home/ctf/flag`等；
* Flag格式为`CISCN{this_is_a_sample_flag}`；
* 出题请参照`challenge_template`文件夹下的出题格式要求。


## 文件解释
* `challenge_template`文件夹，为题目格式模板
    * 文档说明 - README.md
    * 源码 - source文件夹，赛事技术委员审题
    * 附件 - attachments文件夹，提供给选手
    * 部署环境 - deploy文件夹，请按上述要求，使用docker打包。
    * 解题步骤 - 完整解题步骤，必须包含exp。
* `checker`文件夹，为题目功能检查脚本及python服务样例：
    * `my_client.py`与`test_client.py`为checker逻辑,协议相关内容在`my_client.py`,`test_client.py`为
    check逻辑,主要实现了对功能的check,包括表达式计算,简单队列,随机读取队列,两个连接下的顺序随机读取和
    两个连接下交叉随机读取的检验.
    * `service_example.py`为能够通过check的一个简易基本python服务器,可以本机运行该服务器,然后运行
    `test_client.py`进行检验. 检验通过则没有任何报错,如果`test_client.py`出现exception则说明检验未通过.

## checker具体实现过程
1. 在`my_client.py`中,使用XXXpacket说明了协议的格式,`into()`方法将packet转换为bytes类型,`from_bytes()`
方法解析一个bytes类型,根据情况抛出相应异常,可能出现未计算完毕和计算出错两种情况,分别对应两种异常.

2. 在`my_client.py`中,通过`RpcClient`实现了一个rpc的客户端,主要功能为检验表达式计算,正常使用为调用
call方法,传入表达式等待结果,其他方法为检验是否按照消息队列要求实现功能所用. rpc的方法主要为根据协议
构造相应的包,然后通过tcp连接进行传输通信. 建立连接是发送connect包,成功后通过declare包可以在服务端
建立一个消息队列,并且收到reply result包,得到该消息队列的id,之后发送call包发起一个rpc请求,call需要
指定`corr_id`,也就是该请求的id,以及`reply_to`,也就是该请求的结果希望存入的消息队列. 之后,通过retrieve
包去取由一个key指定的消息队列的头部,如果与给出的`corr_id`相同,则弹出,并且返回结果,否则发送retry
包,客户端则应当继续读取. 最后在功能结束后使用close包中止连接

## Server的预期功能
1. 能够实现规定的协议的解析和打包,协议见后
2. 能够完成按照key找到对应的消息队列,消息队列为一个队列数据结构,可以按照先入先出的顺序存取数据,数据
类型为字符串
3. 能够根据字符串进行表达式运算,并且将运算结果放入指定key的消息队列. 每一个运算对应一个`corr_id`,
可以根据id确认是否为该次运算的结果

## 协议格式

```sh
+--------+----------+---------+--------
|magic(4)| length(4)|  type(4)| ...
+--------+----------+---------+-------
```

* magic: 4字节magic,包括'RPCM'和'RPCN'两种,M代表向服务器发送数据,N代表接收服务器数据.
* length: 4字节,大端序,为整个包的总大小,包括magic等header的大小.
* type: 4字节,大端序,包的类型,
* 不同包的类型有不同的自定义格式,总体格式为4字节或8字节大小,紧跟相应的域,大小为所给出的大小,在协议中length可以起验证作用,也可以由于length和后面域大小可以不一致提供一个可能的漏洞点,

### 发送包
#### connect -- type = 0
连接包,在建立连接时确认连接建立成功,表示开启服务,没有自定义域,服务器收到返回done包.

#### declare -- type = 1
分配消息队列包,向服务器请求一个消息队列,分配一个消息队列id作为返回,包含在result包中.

#### retrieve -- type = 2
获取消息包,需要依次提供`key`和`corr_id`两个自定义域,均为字符串,域长度为32位以内.
按照key所对应的消息队列,试图获取`corr_id`请求得到的结果.服务器收到之后确认key所对应的消息队列
目前的队首消息是否为`corr_id`请求的结果,如果不是则返回unavailable包,否则弹出队首结果并且返回result

#### call -- type = 3
发起请求包,依次提供`reply_to`, `corr_id`和`expr`三个域,同样为长度32位以内,均为字符串.
发起一个请求,id为`corr_id`,表达式内容为`expr`,返回结果加入`reply_to`作为key所对应的消息队列.
成功返回done包.

#### close -- type = 4
无自定义域,停止本次连接,服务器接收到该包可以断开连接.

### 返回包
#### Done -- type = 0xbeef
无自定义域,发送包所对应的行为执行成功

#### Error -- type = 0xbeef + 1
无自定义域,发送包所对应的行为执行失败

#### Unavailable -- type = 0xbeef + 2
无自定义域,发送包所对应的行为执行失败,但是可能为结果未计算完毕,应当重新发起

#### Result -- type = 0xbeef + 3
包含`result_bytes`自定义域,发送包所对应的行为执行成功,并且得到一个结果,结果为`result_bytes`,
`result_bytes`长度32位

## 应用场景
请自行基于以上要求，实现自己的应用场景。

本题要求所对应的场景主要为RPC服务,例如启动后台程序完成耗时长的功能等,将web等app的后端的任务执行部分分离,将服务器压力分散. 类似的有`rabbitmq`等.
