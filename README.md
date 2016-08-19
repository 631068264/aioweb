## **Basic aiohttp + aiomysql + aiohttp-jinja2 project**
**这个主要是 FCM(Firebase Cloud Message)** 一个简单消息协程推送接口


用着不爽,写些东西方便自己。向**Flask**用法靠拢 **有时间读读Flask源码**
### 工具:
 - Data validation( get post json) xform.py
 - Log logger.py
 - Route framework.py
 - 代替SQLAlchemy工具 smart*.py (SQLAlchemy用起来好不爽 文档像坨屎 连建model类的时间都省了)
 - 继承Response 重写 JsonResponse TemplateResponse Redirect(通过route_name)
 - Jinjia 模板过滤器  jinjia_filter.py
 - 比较简单的使用列子
    

----------


主要是相关文档有点简略，可能以后用到方便自己.参考一些大神的想法,学到不少

 - 动态import
 - `callable`
 - `__call__ __and__ __lt__` 等神奇的函数
 - Python3 新特性 **asyncio** (一直用Python2的)
 - meataclass apply 在PY3 的转变
 - __getattr__ 
