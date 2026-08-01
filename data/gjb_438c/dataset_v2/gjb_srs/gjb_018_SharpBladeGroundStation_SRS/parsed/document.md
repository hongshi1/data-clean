# 软件需求规格说明书

项目名称： 无人机地面站系统

编 制 人： cfrpg

编制时间： 2018.03.22

目 录

## 1 范围

## 1.1 标识

本文档适用于无人机地面站系统。

系统标识号：无人机地面站系统 V1.0。

标题：无人机地面站系统。

缩略词语：UAVGS。

版本号：1.0。

标识号：1.0。

## 1.2 系统概述

本文档适用于无人机地面站系统 V1.0。

无人机地面站系统是三 X 航空飞控系统及无人机系统配套的上位机软件，具有飞控调试，飞行状态监控，航线任务规划，视频显示，视频信息叠加，日志回放等功能，可用于无人机系统和飞控系统的调试，无人机系统任务飞行规划和控制，以及对飞行结果的分析等工作。

软件运行于 Windows 平台，使用 C# 和 WPF 进行开发。软件目前处于开发初步阶段，已完成软件需求功能确定和软件功能的可行性分析与研究。

软件开发和初步测试阶段运行于普通个人计算机中，测试阶段使用地面站系统硬件运行，投入使用后使用地面站硬件运行，也可使用与地面站系统硬件配置类似的个人计算机运行。

软件开发方为西工大玄学办航空学院分办，软件维护由开发方担任，需求方为三 X 航空，用户为三 X 航空飞控用户及飞控开发人员。

## 1.3 文档概述

本文档描述对计算机软件配置项的需求，及确保每个要求得以满足的所使用的方法。本文档包括对软件功能需求和外部接口的描述，及对运行环境和计算机资源要求的描述。

本文档可由投资方，需方，开发方和支持机构查看。

## 2 需求

## 2.1 功能需求

地面站软件系统功能如图??所示。

![](images/9e9d7637e78ca63259de294c44013e5575070c07c05d0c15047281b4a7b97e7f.jpg)  
图 2-1 地面站系统功能结构图

## 2.1.1 自动扫描连接

地面站系统只会同时与一台无人机建立连接。

当连接正常接入时，软件能够自动识别连接使用的串口，接入的硬件和使用的通讯协议，并在 10s 内与飞控建立连接。连接建立后忽略所有新出现的串口连接。软件通过检测心跳包判断连接是否可用，当一定时间没有接收到心跳包后认为连接断开。心跳包丢失时间可在软件中进行设置。

在建立连接前，若存在无法识别通信协议的串口连接，软件将使用串口通信设置的波特率持续对串口进行扫描，直到出现可识别的串口。

## 2.1.2 串口发送与接收

地面站系统使用串口通过直接连接或经由数传电台与无人机飞控进行通信。串口通信波特率为 115200，可以通过地面站设置更改串口使用的波特率。

当串口意外断开时，软件能够捕获异常并做适当处理，保证运行的稳定。

## 2.1.3 信息解析

地面站系统接收到数据包后，根据通信协议解析接收缓存并提取数据包，供其他功能模块使用，或接受其他功能模块传递的数据包，将其转换为数据流经由串口发送。

## 2.1.4 任务航线规划

地面站系统能够进行任务航线规划，任务由一系列按顺序相连的任务项组成。使用的任务项如表??所示。任务项通过点击地图或输入参数设置，或通过子任务加载或自动生成。任务航线可以保存到本地文件，或从文件中读取。

任务规划完毕后通过串口通信发送至无人机飞控，飞控不支持的任务项类型将被自动忽略。

表 2-1 任务项
<table><tr><td rowspan=1 colspan=1>类别</td><td rowspan=1 colspan=1>任务项</td></tr><tr><td rowspan=1 colspan=1>航路点</td><td rowspan=1 colspan=1>初始点，导航点，起降点，环绕点</td></tr><tr><td rowspan=1 colspan=1>动作</td><td rowspan=1 colspan=1>拍照，投放载荷，模态转换，操作任务载荷</td></tr><tr><td rowspan=1 colspan=1>子任务</td><td rowspan=1 colspan=1>子任务，扫描区域</td></tr><tr><td rowspan=1 colspan=1>飞行控制</td><td rowspan=1 colspan=1>改变速度，改变高度</td></tr></table>

## 2.1.5 无人机指令

地面站系统能够直接向无人机飞控发送指令，指示飞控完成一定的动作。发送的指令主要包括以下几类：

• 飞行指令：控制无人机飞行的指令，包括起飞，降落，返航，飞行模式切换，飞行到目标点等。

• 飞控指令：命令飞控执行动作，包括校准传感器，锁定或解锁飞控，获取和设置飞控参数等。

• 任务指令：与任务相关的指令，包括发送和接收任务或单独的任务项，开始或终止任务等。

指令发送后由地面站判定是否发送成功，若发送失败将自动重发若干次，重发次数可由用户设定。

## 2.1.6 飞行参数显示

地面站系统通过通信系统获取飞行数据，并以一定的方式将其中的部分参数显示在软件界面中。界面中直接显示的数据见表??。所有数值全部使用 SI 单位。

对于不同的飞控硬件，发回的数据内容可能并不相同。若飞控没有发送需要显示的参数，地面站中将显示参数的缺省值。若飞控中途断开连接，软件将保持显示最后一次接收到的数值。

表 2-2 显示的飞行参数
<table><tr><td rowspan=1 colspan=1>参数类型</td><td rowspan=1 colspan=1>参数名</td></tr><tr><td rowspan=1 colspan=1>飞行姿态</td><td rowspan=1 colspan=1>俯仰角，滚转角，机头指向</td></tr><tr><td rowspan=1 colspan=1>飞行状态</td><td rowspan=1 colspan=1>空速，地速，航向，上升/下降率，相对高度，飞行模式</td></tr><tr><td rowspan=1 colspan=1>定位状态</td><td rowspan=1 colspan=1>精度，纬度，卫星数，定位状态，定位误差</td></tr><tr><td rowspan=1 colspan=1>导航状态</td><td rowspan=1 colspan=1>航程，航时，回航角，航点信息</td></tr><tr><td rowspan=1 colspan=1>动力状态</td><td rowspan=1 colspan=1>电池电压，电池电流，估计剩余电量</td></tr><tr><td rowspan=1 colspan=1>通信状态</td><td rowspan=1 colspan=1>通信速率，通信协议，RSSI</td></tr></table>

## 2.1.7 视频显示与叠加

地面站系统能够显示视频画面，同时在画面中叠加部分飞行参数和图形提示。

在无人机飞行时，视频画面由图传电台接收，通过视频采集卡获取视频流进行显示；在回放时，视频从本机硬盘中读取。

## 2.1.8 双屏切换

地面站系统能够拆分为两个窗口，分别显示于两个显示器中。其中一个窗口显示地图和飞行参数，另一个窗口显示机载摄像设备传回的画面。在运行过程中两个显示器中的窗口可以快速交换位置。

若无视频流传入，则摄像画面窗口显示空白内容。

## 2.1.9 地图显示

地面站系统能够显示普通地图，卫星地图或混合地图，并能够在三种地图之间切换。除地图外，还能够在地图上实时显示无人机位置，方向，飞行轨迹和预设航线。

地图使用国内电子地图平台，能够预先缓存指定地区的离线地图，地图上显示误差不超过 0.1m。

## 2.1.10 飞行日志

地面站系统通过通信系统接收到合法的数据包后，将数据包连同时间戳作为飞行日志储存于本地硬盘中，以便回放使用。飞行日志实时写入硬盘临时文件中，当用户选择停止写入或关闭地面站时，将弹出保存窗口用以指定日志文件保存位置。若飞行过程中地面站意外关闭，临时文件没有损坏，则可以通过临时文件恢复意外关闭前的飞行记录。

## 2.1.11 视频记录

地面站系统接收到图传电台传回的视频数据流，将视频原始数据流以视频文件的格式储存在本地硬盘中，同时记录视频时间与飞控运行时间的相对关系。

若飞行过程中地面站意外关闭，视频记录文件将部分损坏。

## 2.1.12 日志回放

地面站系统能够读取飞行日志和视频记录，并进行回放。回放时可以单独回放飞行日志，或同时回放飞行日志和视频画面。回放速度和进度均可以手动实时调节。

当同时回放视频与日志时，飞行参数仍以与飞行时相同的方式叠加在视频上。

## 2.1.13 固件更新

地面站系统能够对飞控固件进行更新和烧写。

## 2.1.14 系统设置

对地面站软件中的部分参数进行设置，并可将设置信息以配置文件的形式保存至文件。

## 2.1.15 配置加载

地面站系统可从外部文件加载配置信息，以快速适配不同的无人机系统或使用环境。

若加载的配置文件与地面站版本不同，加载中将忽略地面站软件不存在配置参数，同时保持文件中没有指明的参数不变。

## 2.2 外部接口需求

## 2.2.1 接口标识和接口图

地面站系统外部接口如图??所示。接口简述如表??所示。

表 2-3 外部接口说明
<table><tr><td rowspan=1 colspan=1>接口名称</td><td rowspan=1 colspan=1>接口简述</td></tr><tr><td rowspan=1 colspan=1>数据通信接口</td><td rowspan=1 colspan=1>使用特定的通讯协议，用于与飞控进行通信，或读取日志文件用于回放</td></tr><tr><td rowspan=1 colspan=1>视频流接口</td><td rowspan=1 colspan=1>用于从外部获取视频数据</td></tr><tr><td rowspan=1 colspan=1>文件接口</td><td rowspan=1 colspan=1>用于向磁盘中写入飞行日志和视频记录，写入或读取配置信息</td></tr><tr><td rowspan=1 colspan=1>用户输入接口</td><td rowspan=1 colspan=1>用于获取操作员对地面站系统的输入</td></tr><tr><td rowspan=1 colspan=1>显示接口</td><td rowspan=1 colspan=1>用于在显示器中绘制图形界面</td></tr></table>

![](images/03fe52f7f93aa813bded2ca733521227051b4c98f8e98ea224b4c25159f341ab.jpg)  
图 2-2 外部接口图

## 2.3 计算机资源需求

## 2.3.1 计算机硬件需求

运行地面站软件的计算机硬件需求配置如表??所示。

表 2-4 计算机硬件需求
<table><tr><td rowspan=1 colspan=1>硬件</td><td rowspan=1 colspan=1>最低需求</td></tr><tr><td rowspan=1 colspan=1>处理器</td><td rowspan=1 colspan=1>Intel Core i5</td></tr><tr><td rowspan=1 colspan=1>内存</td><td rowspan=1 colspan=1>4G 双通道</td></tr><tr><td rowspan=1 colspan=1>图形</td><td rowspan=1 colspan=1>Intel HD530</td></tr><tr><td rowspan=1 colspan=1>储存空间</td><td rowspan=1 colspan=1>1G SSD</td></tr><tr><td rowspan=1 colspan=1>显示</td><td rowspan=1 colspan=1>每个显示器实际分辨率1366*768</td></tr><tr><td rowspan=2 colspan=1>其他</td><td rowspan=1 colspan=1>至少一个 USB 接口</td></tr><tr><td rowspan=1 colspan=1>支持 DirectShow 的视频采集卡</td></tr></table>

其中储存空间需求为保证地面站正常运行和记录日志的最低要求，不包含储存飞行视频的空间需求。

## 2.3.2 计算机软件需求

• Windows 7 及以上的 Windows 操作系统

• Microsoft .NET Framework 4.5

• Microsoft .NET Framework 4.0

• Microsoft DirectX 9.0c 及以上

• 用于连接数传电台和飞控的串口驱动程序

• 视频采集相关驱动程序

## 3 合格性规定

各个功能使用的合格性方法如表??所示。其中演练包括任何可能出现的合法或非法操作。使用对应合格性方法确认地面站系统能够稳定的完成??节中的所有功能和任务。

表 3-1 合格性方法
<table><tr><td rowspan=2 colspan=1>功能需求</td><td rowspan=1 colspan=3>合格性方法</td></tr><tr><td rowspan=1 colspan=1>演练</td><td rowspan=1 colspan=1>测试</td><td rowspan=1 colspan=1>分析</td></tr><tr><td rowspan=1 colspan=1>自动扫描连接</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>串口发送与接收</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td></tr><tr><td rowspan=1 colspan=1>信息解析</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>任务航线规划</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>无人机指令</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>飞行参数显示</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>双屏切换</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>地图显示</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>飞行日志</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>视频记录</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>日志回放</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>固件更新</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>系统设置</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>配置加载</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1>•</td><td rowspan=1 colspan=1></td></tr></table>