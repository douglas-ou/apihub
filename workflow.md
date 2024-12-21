# API Hub

0. 建立一个 API provider 库, 存储 API 项目的名称/描述，文档站 URL，方便开发者进行快速索引搜索

Input: 
* 用户选择/搜索到一个 API 项目，或者自己输入 API 文档站的 url

-> 文档站 url

Workflow
1. 爬取 url, 视图寻找其中的 openapi.json，找到则直接返回
2. 遍历文档站 url 的子网页，找到其中属于是 API 文档的页面，将对应的 url 与内容缓存成列表
3. 异步解析所有的文档站 url 页面，将对应的接口转化为 OpenAPI.json 格式的接口文档
4. 将页面 url 的解析结果组合起来，形成整个文档站的 openapi.json，保存到 API provider 中

对于 openapi.json 文档，开发者可以轻松检索，调试和管理接口，后续也可以直接接入 API chatbot 或监控管理功能, 如

### API 接入开发
* Input: 我希望实现 XXX 功能，如何调用这个 API 实现
* Output: 对应的接口文档（+原始链接），API 的用法（所需要的字段高亮），示例请求代码

### API 接口管理
直接使用 [UtilMeta 平台](https://beta.utilmeta.com/) 进行接口管理，监控，测试等

