# 快速开始

下文以 **Windows** 为例。把发行包解压后的目录称为 `SERVER_HOME`（例如 `D:\openOntology`，该目录下应能看到 `bin` 文件夹）。

## 1. 安装 JDK 25 并设置 JAVA_HOME

本系统需要 **JDK 25 或更高**。装完后还须设置环境变量 `JAVA_HOME`（安装程序不一定会设）。

1. 打开 [Oracle JDK 下载页](https://www.oracle.com/java/technologies/downloads/)，选择 **JDK 25**、Windows，下载并按向导安装  
2. 记下安装目录（常见 `C:\Program Files\Java\jdk-25`，其下应有 `bin\java.exe`）  
3. 右键「此电脑」→「属性」→「高级系统设置」→「环境变量」，新建用户或系统变量：  
   - 变量名：`JAVA_HOME`  
   - 变量值：上面的 JDK 安装目录  

## 2. 启动

在资源管理器中打开 `D:\openOntology\bin`（改成你的解压目录），双击 `startup.bat`。会弹出一个黑色窗口，请保持打开。

浏览器打开：

```text
http://localhost:8825/
```

## 3. 系统初始化（首次必做）

首次进入会跳到初始化页：配一个大模型，并导入演示域。

![系统初始化](images/init.png)

**左侧 · 大模型**

1. 点 **使用 DeepSeek**  
2. 按弹窗申请 API Key（打开 [DeepSeek 开放平台](https://platform.deepseek.com)，登录后创建密钥；这是调用大模型的密钥，不是软件 License）  
3. 粘贴密钥，可先 **测试连接**，再 **保存**

**右侧 · 业务域**

点 **导入零售测试数据**（一键安装演示域）。

完成后即可进入系统。

## 4. 试问

1. 顶栏确认已选中演示域  
2. 打开 **智能体工作台**  
3. 提问，例如：「哪些客户卖的比较好，为什么？」
