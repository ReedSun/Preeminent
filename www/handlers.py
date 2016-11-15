#!/usr/bin/env python3
# -*- coding: utf-8 -*-


' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

# markdown2模块是一个支持markdown文本输入的模块，是Trent Mick写的开源模块，我们将其拷贝在本文件夹中，在这里调用
import markdown2  

from aiohttp import web

from coroweb import get, post
from apis import APIValueError, APIResourceNotFoundError, APIError, APIPermissionError, Page

from models import User, Comment, Blog, next_id
from config import configs

COOKIE_NAME = 'awesession'  # cookie名，用于设置cookie
_COOKIE_KEY = configs.session.secret  # cookie密钥，作为加密cookie的原始字符串的一部分


# 这个函数在day11被定义
# 在api_create_blog()（实现博客创建功能）中被调用 
# 验证用户身份
# 如果没有用户或用户没有管理员属性，报错
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


# 这个函数在day11中被定义
# 作用是获取页码
def get_page_index(page_str):
    # 将传入的字符转化为页码信息
    # 实际上就是对页码信息做合法化检查
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


# 这个函数在day10中定义
# 通过用户信息计算加密cookie
def user2cookie(user, max_age):
    '''
    Generate cookie str by user.根据用户信息生成cookie
    '''
    # build cookie string by: id-expires-sha1
    # 根据id、过期日期、sha1值生成字符串
    # expires（失效时间）是当前时间加cookie最大存活时间的字符串
    expires = str(int(time.time() + max_age))
    # 利用用户id，加密后的密码，失效时间，加上cookie密钥，组合成待加密的原始字符串
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    # 生成加密的字符串，并于用户id，失效时间共同组成cookie
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

# 这个函数在day11中被定义
# 文本转html
# 这个函数在get_blog()中被调用
def text2html(text):
    # 先用filter函数对输入的文本进行过滤处理，断行，去收尾空白字符
    # 再用map函数对特殊符号进行转换，在将字符串装入html的<p>标签中
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    # lines是一个字符串列表，该字符串即表示html的段落
    return ''.join(lines)

# 这个函数在day10中被定义
# 解密cookie
@asyncio.coroutine
def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.如果cookie是有效的，分析cookie，加载用户信息
    '''
    if not cookie_str:
        return None
    try:
        # 解密是加密的逆向过程，因此，先通过“-”拆分cookie，得到用户id，失效时间，以及加密字符串
        L = cookie_str.split('-') # 返回一个str的list
        if len(L) != 3: # cookie应该是由三部分组成的，如果得到的不是三部分，则显然出错了
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time(): # 如果过了失效时间，则cookie失效了
            return None
        user = yield from User.find(uid)  # 在数据库中查找用户信息
        if user is None:  # 如果不存在用户名，则也出错了
            return None
        # 再用sha1处理得到的信息，与cookie里的sha1对象做对比
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        # 如果不一致，则说明出错了
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        # 验证cookie就是为了验证当前用户是否在登陆状态，从而使用户不必再进行登陆
        # 因此 返回用户信息即可
        return user
    except Exception as e:
        logging.exception(e)
        return None

# ----------------------------------页面定义区--------------------------------

# day14中定义
# 页面：首页
@get('/')
@asyncio.coroutine
def index(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber('count(id)')
    page = Page(num, page_index)
    if num == 0:
        blogs = []
    else:
        blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
    # 返回一个模板，指示使用何种模板，模板的内容
    # app.py的response_factory将会对handler.py的返回值进行分类处理
    return {
        '__template__': 'blogs.html',
        'page': page,
        'blogs': blogs
    }


# day11定义
# 页面：博客详情页
@get('/blog/{id}')
@asyncio.coroutine
def get_blog(id, request):
    blog = yield from Blog.find(id)  # 通过id从数据库中拉去博客信息
    # 从数据库拉取指定blog的全部评论，按时间降序排序，即最新的排在最前
    comments = yield from Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    # 将每条评论都转化成html格式
    for c in comments:
        c.html_content = text2html(c.content)
    # blog也是markdown格式，将其转化成html格式
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
          '__user__':request.__user__,
        'comments': comments
    }


# day10中定义
# 页面：注册页面
@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

# 页面：登陆页面
@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }

# day12中定义
# 页面：日志列表页
@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }


# day11中定义
# 页面：日志创建页
@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',  # id的值将传给js变量I
        # action的值也将传给js变量action
        # 将在用户提交博客的时候，将数据post到action制定的路径，此处即为创建博客的api
        'action': '/api/blogs'
    }



# day14定义
# 管理重定向
@get('/manage/')
def manage():
    return 'redirect:/manage/comments'


# day14定义
# 页面：评论列表页
@get('/manage/comments')
def manage_comments(*, page='1'):
    return {
        '__template__': 'manage_comments.html',
        'page_index': get_page_index(page)
    }

# day14定义
# 页面：修改博客页
@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
    return {
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/%s' % id
    }

# day14定义
# 页面：用户管理
@get('/manage/users')
def manage_users(*, page='1'):  # 管理页面默认从1开始
    return {
        '__template__': 'manage_users.html',
        'page_index': get_page_index(page)  # 通过page_index来显示分页
    }



# ----------------------------------API 功能定义区---------------------------

# API：获取用户信息
@get('/api/users')
async def api_get_users():
    users = await User.findAll(orderBy="created_at desc")
    for u in users:
        u.passwd = "*****"
    # 以dict形式返回,并且未指定__template__,将被app.py的response factory处理为json
    return dict(users=users)

# API:用户注册
# 在register.html中将会通过/api/users调用
# 首先，预编译正则表达式
# 第一个_RE_EMAIL中的字符含义
# ^表示行的开头
# [a-z0-9\.\_]+表示匹配至少一个字母或数字或.或-或_
# \@表示匹配@
# [a-z0-9\-\_]+表示匹配至少一个字母或数字或-或_（不匹配.）
# (\.[a-z0-9\-\_]+){1,4}表示这是一个一个字符到四个字符的分组，匹配第一个字符是.之后匹配字母或数字或-或_
# $表示行的结尾
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
# [0-9a-f{40}表示匹配40个数字或a-f的字母
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')
@post('/api/users')
@asyncio.coroutine
def api_register_user(*, email, name, passwd):  # 注册信息包括用户名邮箱与密码
    # 验证输入的正确性
    # 如果没输入name
    if not name or not name.strip():  # s.strip(rm)函数表示删除s字符串中开头、结尾处，位于rm删除序列的字符
                                      # 如果rm为空时，默认删除空白字符
        raise APIValueError('name')
    # 如果email不符合正则表达式匹配的格式
    if not email or not _RE_EMAIL.match(email): 
        raise APIValueError('email')
    # 如果passwd不符合SHA1算法的正则表达式格式
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    # 在数据库里查看是否已存在该email
    users = yield from User.findAll('email=?', [email])
    # users的长度不为零即意味着数据库已存在同名email，抛出异常错误
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')

    # 数据库无相应的email信息，说明是第一次注册
    uid = next_id()   # next_id是models函数里的用于生成一个基于时间的独一无二的id，作为数据库表中每一行的主键
    sha1_passwd = '%s:%s' % (uid, passwd)  # 将用户id和密码组合
    # 创建用户对象，其中密码不是用户输入的密码
    # unicode格式的对象在进行哈希运算时必须先编码成utf8格式
    # hashlib.sha1()表示计算一个字符串的sha1值
    # hash.hexdigest()函数将hash对象转换成16进制表示的字符串
    # 密码用的是sha1算法，而邮箱用的是md5算法
    # Gravatar是一项在全球范围内使用的头像服务，不过在中国好像被墙了
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    yield from user.save()  # 将用户信息储存到数据库中

    # make session cookie:
    r = web.Response()
    # 刚创建的的用户设置cookie(网站为了辨别用户身份而储存在用户本地终端的数据)
    # http协议是一种无状态的协议,即服务器并不知道用户上一次做了什么.
    # 因此服务器可以通过设置或读取Cookies中包含信息,借此维护用户跟服务器会话中的状态
    # user2cookie设置的是cookie的值，在前面定义的
    # max_age是cookie的最大存活周期,单位是秒.当时间结束时,客户端将抛弃该cookie.之后需要重新登录
    # 设置最大存活周琪是24小时
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'  # 修改密码的外部显示为*
    # 设置content_type，将在data_factory中间件中继续处理
    r.content_type = 'application/json'
    # json.dump方法将对象序列化为json格式
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r



# API：用户登录
@post('/api/authenticate')
@asyncio.coroutine
def authenticate(*, email, passwd):  # 通过邮箱与密码验证登陆
    # 验证是否输入了邮箱和密码
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    # 在数据库中查找email，将以list的形式返回
    users = yield from User.findAll('email=?', [email])
    # 如果list长度为0，则说明数据库中没有相应的纪录，即用户不存在
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0] # 取得用户记录.事实上,就只有一条用户记录,只不过返回的是list
    # 验证密码:
    # 数据库中存储的并非原始的用户密码,而是加密的字符串
    # 我们对此时用户输入的密码做相同的加密操作,将结果与数据库中储存的密码比较,来验证密码的正确性
    # 以下步骤合成为一步就是:sha1 = hashlib.sha1((user.id+":"+passwd).encode("utf-8"))
    # 对照用户注册时对原始密码的操作(见api_register_user),操作完全一样
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    # 登录密码验证成功，设置cookie:
    # 与注册用户部分代码完全一样
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

# 实现用户登出
@get('/signout')
def signout(request):
    # 请求头部的referer，表示从哪里链接到当前页面的，即获得上一个页面
    referer = request.headers.get('Referer')
    # 如果referer为None，则说明无前一个网址，可能是用户新打开了一个标签页，则登陆后转到首页
    r = web.HTTPFound(referer or '/')
    # 通过设置cookie的最大存活时间来删除cookie，从而使登陆状态消失
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out.')
    return r


# day11定义
# API：实现获取单条博客信息的功能
@get('/api/blogs/{id}')
@asyncio.coroutine
def api_get_blog(*, id):
    blog = yield from Blog.find(id)
    return blog

# day11定义
# API：实现博客创建功能
@post('/api/blogs')
@asyncio.coroutine
def api_create_blog(request, *, name, summary, content):
    check_admin(request) # 检查用户权限
    # 验证博客信息的合法性
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    # 创建博客对象
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
    yield from blog.save()  # 储存博客到数据库中
    return blog  # 返回博客信息


# day12定义
# API:获取博客
@get('/api/blogs')
@asyncio.coroutine
def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber('count(id)') # num为博客总数
    p = Page(num, page_index)  # 创建Page对象（Page对象在apis.py中定义）
    if num == 0:
        return dict(page=p, blogs=())  # 若博客数为0,返回字典,将被app.py的response中间件再处理
    # 博客总数不为0,则从数据库中抓取博客
    # limit强制select语句返回指定的记录数,前一个参数为偏移量,后一个参数为记录的最大数目
    blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)  # 返回字典,以供response中间件处理

# day14定义
# API：获取评论
@get('/api/comments')
@asyncio.coroutine
def api_comments(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Comment.findNumber('count(id)')  # num为评论总数
    p = Page(num, page_index)  # 创建Page对象，保存页面信息
    if num == 0:
        return dict(page=p, comments=())  # 若评论数为零，返回字典，将会被app.py的response中间件再处理
    # 博客总数不为0,则从数据库中抓取博客
    # limit强制select语句返回指定的记录数,前一个参数为偏移量,后一个参数为记录的最大数目
    comments = yield from Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, comments=comments)

# day14定义
# API：创建评论
@post('/api/blogs/{id}/comments')
@asyncio.coroutine
def api_create_comment(id, request, *, content):
    user = request.__user__
    # 验证用户
    if user is None:
        raise APIPermissionError('Please signin first.')
    # 验证评论内容是否存在
    if not content or not content.strip():
        raise APIValueError('content')
    # 验证博客是否存在
    blog = yield from Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    # 创建评论对象
    comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
    yield from comment.save()  # 储存评论到数据库中
    return comment  # 返回评论

# day14定义
# API：删除评论
@post('/api/comments/{id}/delete')
@asyncio.coroutine
def api_delete_comments(id, request):
    check_admin(request)  #查看权限，是否是管理员
    c = yield from Comment.find(id)  # 从数据库中拉去评论
    if c is None:
        raise APIResourceNotFoundError('Comment')
    yield from c.remove()  # 删除评论
    return dict(id=id)  # 返回被删除评论的id

# day14定义
# API:修改博客
@post('/api/blogs/{id}')
@asyncio.coroutine
def api_update_blog(id, request, *, name, summary, content):
    check_admin(request)  # 检查用户权限
    blog = yield from Blog.find(id)  # 从数据库中拉去修改前的博客
    # 检查博客的合法性
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    yield from blog.update()  # 更新博客
    return blog  # 返回博客信息

# day14定义
# API:删除博客
@post('/api/blogs/{id}/delete')
@asyncio.coroutine
def api_delete_blog(request, *, id):
    check_admin(request)
    blog = yield from Blog.find(id)
    yield from blog.remove()
    return dict(id=id)