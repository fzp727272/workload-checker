# HELPSHERRY：周报wiki解析与分析框架

## 主要功能

### 配置参数
1. 所有的参数目前都在config.json文件中配置
2. 参数有"base_url":获取wiki信息的链接；"username": wiki的账户名；"api_token":wiki的APItoken，在这里拿 https://id.atlassian.com/manage-profile/security/api-tokens"；"dify_api_key":dify的apikey；pageid：页面的pageid，比如“https://decathlon.atlassian.net/wiki/spaces/CHIN/pages/2338947945/W9_2026.02.27”这个中pages后面“2338947945”这段数字


### 获取wiki
1. 处理脚本为getWiki.py文件，是通过confluence的API来通过wiki中pageID来获取
2. 调用的APIkey是zhengpeng在decathlon的confluence账号，所以必须zhengpeng有权限的才能下载到wiki文件，否则报错
3. getWiki需要传入pageID，pageid就是比如“https://decathlon.atlassian.net/wiki/spaces/CHIN/pages/2338947945/W9_2026.02.27”这个中pages后面“2338947945”这段数字
4. pageID可以是一个数组传入，意味着你可以批量下载多个page的wiki，每个会单独写进一个txt文件，文件会存入wiki的文件夹下面

### 分析wiki
1. 处理脚本为anayzeByDify.py文件，通过调用dify工作流来识别拆分wiki信息
2. 目前dify链接 https://dify-console.pp.dktapp.cloud/app/296a75e6-4296-4c57-b941-faf12d9f22f6/workflow
3. dify目前使用deepseek V3.1版本，不建议使用Qwen，提示词在"提示词.md"文档
4. dify目前使用pp环境可能存在不稳定，后续可尝试切到其他平台
5. anayzeByDify.py可单独执行，单独支持会把整个wiki文件中所有的text文件发送给dify处理
6. 处理成功后会生成.csv表格文件和json格式文件，其中.csv可用于统计
7. 因为AI的幻觉问题建议生成表格后人工检验并存档后续统计分析可在存档文件中进行

### 报告生成
1. 处理脚本为report.py,通过python分析表格来做数据统计
2. 目前会根据几个维度来进行统计，每个设计师的工时，项目工时，业务部门工时等
3. 后续可以根据需求来做定制，这个不难，不会代码的同学可以将表格的格式传给AI，让AI根据自己的需要做一个基于pandas的数据统计python脚本

## 目前问题
1. dify的工作流存在输出