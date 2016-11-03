import asyncio, os, inspect, logging, functools
from urllib import parse
from aiohttp import web
from apis import APIError


# 这是个装饰器，在handlers模块中被引用，其作用是给http请求添加请求方法和请求路径这两个属性
# 装饰器可以详见之前的教程
# 这是个三层嵌套的decorator（装饰器），目的是可以在decorator本身传入参数
def get(path):
    '''
    定义装饰器 @get（"/path")
    '''
    def decorator(func):  # 传入参数是函数
        # python内置的functools.wraps装饰器作用是把装饰后的函数的__name__属性变为原始的属性
        # 因为当使用装饰器后，函数的__name__属性会变为wrapper
        @functools.wrap(func)                    
        # 这个函数直接返回原始函数
        def wrapper(*args, **kw):
            return  func(*args, **kw)
        wrapper.__method__ = "GET"  # 给原始函数添加请求方法 “GET”
        wrapper.__route__ = path  # 给原始函数添加请求路径 path
        return wrapper
    return decorator
# 这样，一个函数通过@get(path)的装饰就附带了URL信息

def post(path):
    '''
    定义一个装饰器 @post("/path")
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return unc(*args, **kw)
        wrapper.__method__ = "POST"
        wrapper.__route__ = path
        return wrapper
    return decorator


# 函数的参数fn本身就是个函数，下面五个函数是针对fn函数的参数做一些处理判断
def get_required_kw_args(fn):
    args = []  # 定义一个空的list，用来储存fn的参数名
    # params将得到一个包含fn的所有参数（输入值）的字典
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        # 如果参数类型为命名关键词参数而且没有指定默认值
        if params.kind = inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)  # 把命名关键字参数的参数名加入args中
    return tuple(args)

# 和上一个函数基本一样，区别在于这个函数直接选出所有命名关键词参数的名字，不需要没有制定默认值这个条件，这个
def get_name_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if params.kind = inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

# 判断fn有没有命名关键词参数，如果有就输出True
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.itmes():
        if params.kind == inspect.Parameters.KEYWORD_ONLY:
            return True

# 判断fn有没有关键词参数，如果有就输出True
def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if params.kind == inspect.Parameter.VAR_KEYWORD:
            return True

# 判断fn的参数中有没有参数名为request的参数
def has_request_arg(fn):
    # 这里是把之前函数的一句语句拆分为两句，拆分原因是后面要使用中间量sig
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False  # 这个函数默认输出没有（参数名为request的参数)
    for name, param in params.items():
        if name == "request":
            found = True
            continue  # 下面的代码不执行，直接进入下一个循环
        # 如果找到了request参数，又找到了其他参数是POSITIONAL_OR_KEYWORD（不是VAR_POSITIONAL、KEYWORD_ONLY、VAR_KEYWORD参数）
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError("request必须是最后一个POSITIONAL_OR_KEYWORD类型的参数")
        return found



class RequestHandler(object):

    # 初始化自身的属性
    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    # 定义__call__参数后这个类就相当于一个函数了，可以被调用
    async def __call__(self, request):
        kw = None
        # 如果fn有命名函数或关键字函数
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            # content_type是request提交的消息主体类型，没有就返回丢失消息主体类型
            if request.method = "POST":
                # content_type是request提交的消息主体类型，没有就返回丢失消息主体类型
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')
                # 把request.content_type转化为小写
                ct = request.content_type.lower()
                # 如果消息主体类型开头为application/json，则说明消息主体是个json对象
                if ct.startswith("application/json"):
                    params = await request.json()  # 用json方法读取信息
                    if not isinstance(params, dict):  # 如果读取出来的信息类型不是dict
                        # 那json对象一定有问题
                        return web.HTTPBadRequest("JSON body must be object.")
                    kw = params  # 把读取出来的dict赋值给kw
                elif ct.startswith("application/x-www-form-urlencode") or ct.startswith("multipart/form-data"):
                    params= await request.post()  # 浏览器表单信息用post方法读取
                    kw= dict(**params)
                else:  # post的消息主体既不是json对象，又不是浏览器表单，只能返回不支持该消息主体类型
                    return web.HTTPBadRequest("Unsupported Content-Type: %s" % request,content_type)
            if request.method == "GET":
                qs = request.query_string # 获取请求字符串
                if qs :
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self,_named_kw_args: # 没有关键词参数但是有命名关键字参数
                # 这一块是为了将kw中的不是命名关键字参数去掉
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            for k, v in request.match_info.items():
                # 将kw中的重复参数名报警
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg: # 如果有request参数
            kw["request"] = request
        if self._required_kw_args:  # 如果有未指定默认正的命名关键字参数
            for name in self._required_kw_args:
                if not name in kw:  # kw必须包含全部未制定默认值的命名关键字参数，如果发现遗漏则说明有参数没传入
                    return web.HTTPBadRequest("Missing argument: %s" % name)
        logging.info("call with args: %s" % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data-e.data, message=e.message)

# 向app中添加静态文件目录
def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    app.router.add_static("/static/", path)
    logging.info("add static %s => %s" % ("/static/", path))

# 把请求处理函数注册到app                                
def add_route(app, fn):
    method = getattr(fn, "__method__", None)  # 提取函数中的方法属性
    path = getattr(fn, "__route__", None)  # 提取函数中的路径属性
    if path is None or method is None:  # 如果两个属性其中之一没有值，那就会报错
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)  # 如果函数既不是一个协程，也不是一个生成器，那就把函数变成一个协程
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))  # 把函数注册到app

# 将handlers模块中所有请求处理函数提取出来交给add_route去处理
def add_routes(app, module_name):
    # 如果handlers模块在当前目录下，传入的module_name就是handlers
    # 如果handlers模块
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)

async def logger_factory(app, handler):
    async def logger(request):
        # 记录日志:
        logging.info('Request: %s %s' % (request.method, request.path))
        # 继续处理请求:
        return await handler(request)
    return logger

async def response_factory(app, handler):
    async def response(request):
        # 结果:
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            ...
