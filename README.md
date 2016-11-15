# Preeminent

- 这是一个在[Pyhon教程 - 廖雪峰的官方网站](http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000)中的实战项目帮助下完成的一个博客项目。

- `preeminent`译为卓越的，杰出的。正如此意义，我希望我的bolg作品也能是一个优秀的作品。


## Preeminent项目总结

历时21天时间，终于完成了这个Web APP项目。现在到了做总结的时候了~

完成了这个项目，首先要感谢[廖雪峰](http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000)廖大给我们无私的带来了这么优秀的Python教程和实战教程，让我从一个程序小白变成了一个懂点python的小白~ 

其次要感谢在廖大教程下面讨论问题和提出问题的学友们，正是你们的讨论让我在想放弃的时候又坚持了下来，而且大家相互讨论解决问题，也让我在完成实战项目时避开了好多坑。遇到了程序跑不通我又解决不了的时候~我总是第一个想到来评论区取取经。感谢大家~

还要非常非常非常非常感谢已经完成这个实战教程并提供了大量源码注释的同学们，他们是[xwlyy](https://github.com/xwlyy/awesome-python3-webapp)、[KaimingWan](https://github.com/KaimingWan/PureBlog)、[zhouxinkai](https://github.com/zhouxinkai/awesome-python3-webapp)、[Engine-Treasure](https://github.com/Engine-Treasure/awesome-python3-webapp)，非常感谢，给你们点星星啦哈哈~

最后，还是要感谢我自己，在实战进行到中间的时候，因为代码太复杂，我也曾一度想放弃，但最后还是坚持了下来。感谢坚持着努力着的自己~

总结一下这个项目，我做了如下几个方面的工作。

- 编写了一个用元类编写的ORM，在其中封装了SQL语句， 这样不用直接操作SQL语句，直接使用我们定义好的函数就可以了，关于元类和ORM的简单总结，我写了一篇博客，[Python中的元类Metaclass](http://blog.csdn.net/weixin_35955795/article/details/52985170)。

- 在`aiohttp`框架的基础上，使我们可以直接通过从`handle`模块中定义的页面和API来实现功能，而不用频繁操作底层函数。这个框架主要包括：
 - 定义了`get()`和`post()`两个装饰器来把一个函数映射为一个URL处理函数；
 - 定义了一个`RequestHandler()`类来封装一个URL处理函数，关于`RequstHandler()`类中的一些逻辑我做了一张思维导图来帮助理解，[思维导图](https://github.com/ReedSun/Preeminent/blob/master/www/RequestHandler.png)；
 - 定义了`app_route()`和`app_routes()`来批量注册URL处理函数。
 
- 编写了配置文件`config.py`，其中封装了默认配置文件`config_default.py`和更新配置文件'config_override.py`。

- 定义了Web APP主文件`app.py`，在其中包括：
 - 初始化jinja2模板，配置jinja2的默认环境；
 - 定义了`logger_factory`、`auth_factory`、`data_factory`、`response_factory`四个middleware拦截器，目的是给每个URL处理函数添加一些通用的功能；
 - 通过调用asyncio实现异步IO。
 
- 编写了`handler.py`，在其中就包括了所有页面处理函数和页面功能的实现函数。

- 关于HTML前端页面，我们使用了`uikit`这个css框架，同时基本仿照廖大的页面进行了简单的修改，由于对JavaScript不懂，这里许多地方就直接复制粘贴了- -!


###**一切还没有结束，一切才刚刚开始！**###
完成了这个项目只是一个开始，接下来我打算学习前端方面的知识，加油~