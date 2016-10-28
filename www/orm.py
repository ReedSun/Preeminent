import asyncio
import logging
# aiomysql是Mysql的python异步驱动程序，操作数据库要用到
import aiomysql


# 这个函数的作用是输出信息，让你知道这个点程序在做什么
def log(sql, args=()):
    logging.INFO("SQL语句：%s" % sql)

# 创建全局连接池
# 这个函数将来会在app.py的init函数中引用
# 目的是为了让每个HTTP请求都能从连接池中直接获取数据库连接
# 避免了频繁关闭和打开数据库连接
async def create_pool(loop, **kw):
    logging.info("创建数据库连接池。。。")
    # 声明变量__pool是一个全局变量，如果不加声明，__pool就会被默认为一个私有变量，不能被其他函数引用
    global __pool
    # 调用一个自协程来创建全局连接池，create_pool的返回值是一个pool实例对象
    __pool = await aiomysql.create_pool(
        # 下面就是创建数据库连接需要用到的一些参数，从**kw（关键字参数）中取出来
        # kw.get的作用应该是，当没有传入参数是，默认参数就是get函数的第二项
        host=kw.get("host", "localhost"),  # 数据库服务器位置，默认设在本地
        port=kw.get("port", 3306),  # mysql的端口，默认设为3306
        user=kw["user"],  # 登陆用户名，通过关键词参数传进来。
        password=kw["password"],  # 登陆密码，通过关键词参数传进来
        db=kw["db"],  # 当前数据库名
        charset=kw.get("charset", "utf-8"),  # 设置编码格式，默认为utf-8
        autocommit=kw.get("autocommit", True),  # 自动提交模式，设置默认开启
        maxsize=kw.get("maxsize", 10),  # 最大连接数默认设为10
        minsize=kw.get("minsize", 1),  # 最小连接数，默认设为1，这样可以保证任何时候都会有一个数据库连接
        loop=loop  # 传递消息循环对象，用于异步执行
    )

# =================================以下是SQL函数处理区====================================
# select和execute方法是实现其他Model类中SQL语句都经常要用的方法

# 将执行SQL的代码封装仅select函数，调用的时候只要传入sql，和sql所需要的一些参数就好
# sql形参即为sql语句，args表示填入sql的参数值
# size用于指定最大的查询数量，不指定将返回所有查询结果
async def select(sql, args, size=None):
    log(sql, args)
    # 声明全局变量，这样才能引用create_pool函数创建的__pool变量
    global __pool
    # 从连接池中获得一个数据库连接
    # 用with语句可以封装清理（关闭conn)和处理异常工作
    with (await __pool) as conn:
        # 等待连接对象返回DictCursor可以通过dict的方式获取数据库对象，需要通过游标对象执行SQL
        cur = await conn.cursor(aiomysql.DictCursor)
        # 设置执行语句，其中sql语句的占位符为？，而python为%s, 这里要做一下替换
        # args是sql语句的参数
        await cur.execute(sql.replace("?", "%s"), args or ())
        # 如果制定了查询数量，则查询制定数量的结果，如果不指定则查询所有结果
        if size:
            rs = await cur.fetchmany(size)  # 从数据库获取指定的行数
        else:
            rs = await cur.fetchall()  # 返回所有结果集
        await cur.close
        logging.info("返回的行数：%s" % len(rs))
        return rs  # 返回结果集

# 定义execute()函数执行insert update delete语句
async def execute(sql, args):
    # execute()函数只返回结果数，不返回结果集，适用于insert, update这些语句
    log(sql)
    with (await __pool) as conn:
        try:
            cur = await conn.cursor()
            await cur.execute(sql.replace("?", "%s"), args)
            affected = cur.rowcount  # 返回受影响的行数
            await cur.close()
        except BaseException as e:
            raise
        return affected


# =====================================Model基类，以及其元类区========================


# 定义所有ORM映射的基类Model， 使他既可以像字典那样通过[]访问key值，也可以通过.访问key值
# 继承dict是为了使用方便，例如对象实例user['id']即可轻松通过UserModel去数据库获取到id
# 元类自然是为了封装我们之前写的具体的SQL处理函数，从数据库获取数据
# ORM映射基类,通过ModelMetaclass元类来构造类
class Model(dict, metaclass=ModelMetaclass):
    # 这里直接调用了Model的父类dict的初始化方法，把传入的关键字参数存入自身的dict中
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    # 获取dict的key
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model'模块没有（%s）这个属性" % key)

    # 设置dict的值的，通过d.k = v 的方式
    def __setattr__(self, key, value):
        self[key] = value

    # 获取某个具体的值即Value,如果不存在则返回None
    def getValue(self, key):
        # getattr(object, name[, default]) 根据name(属性名）返回属性值，默认为None
        return getattr(self, key, None)

    # 与上一个函数类似，但是如果这个属性与之对应的值为None时，就需要返回定义的默认值
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            # self.__mapping__在metaclass中，用于保存不同实例属性在Model基类中的映射关系
            # # field是一个定义域!
            field = self.__mappings[key]
            # 如果field存在default属性，那可以直接使用这个默认值
            if field.default is not None:
                # 如果field的default属性是callable(可被调用的)，就给value赋值它被调用后的值，如果不可被调用直接返回这个值
                value = field.default if callable(field.default) else field.default
                logging.debug("为（%s: %s）使用默认值" % (key, str(value)))
                # 把默认值设为这个属性的值
                setattr(self, key, value)
        return value

    # Model类添加class方法，就可以让所有子类调用class方法
    @ classmethod  # 这个装饰器是类方法的意思，即可以不创建实例直接调用类方法
    async def find(cls, pk):
        '''查找对象的主键'''
        rs = await select("%s where `%s`=?" % (cls.__select__, slc.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    # 往Model类添加实例方法，就可以让所有子类调用实例方法
    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.info("无法插入纪录，受影响的行：%s" % rows)


# 父定义域，可以被其他定义域继承
class Field(object):
    # 定义域的初始化，包括属性（列）名，属性（列）的类型，主键，默认值
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default  # 如果存在默认值，在getOrDefault()中会被用到

    # 定制输出信息为 类名，列的类型，列名
    def __str__(self):
        return "<%s, %s:%s>" % (self.__class__.name, self.column_type, self.name)


# 定义映射varchar（可变长度字符串）的SrtingField
class StringField(Field):
    def __init__(self, name=None, primary_key=None, default=None, ddl=varchar(100)):
        super().__init__(name, ddl, primary_key, default)


# 通过ModelMetaclass将具体的子类的映射信息读取出来
class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        # 排除Model类本身
        if name == Model:
            return type.__new__(cls, name, bases, attrs)
        # 获取table名称
        tableName = attrs.get("__table__", None) or name
        logging.info("发现 Model:%s(table:%s" % (name, tableName))
        # 获取所有的Field和主链名
        mappings = dict()
        fields = []
        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info("发现映射：%s ==> %s" % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键
                    if primaryKey:
                        raise RuntimeError("字段的重复主键:%s" % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError("未找到主键")
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs["__mappings__"] = mappings  # 保存属性和列的映射关系
        attrs["__table"] = tableName
        attrs["__primary_key__"] = primaryKey  # 主键属性名
        attrs["__field__"] = fields  # 除主键外的属性名
        # 构造默认的SELECT, INSERT, UPDATE, DELETE语句
        attrs["__select__"] = "select `%s`, %s from `%s`" % (primaryKey, ",".join(escaped_fields), tableName)
        attrs["__insert__"] = " insert into `%s` (%s, `%s`) values (%s)" % (tableName, ",".join(escaped_fields), primaryKey, create_args_string(len(escaped_fields()+1)))
        attrs["__update__"] = "update `%s` set %s where `%s`=?" % (tableName, ",".join(map(lambda f: "`%s`=?" % (mappings.get(f).name or f), fields)), primaryKey)
        attrs["__delete__"] = "delete from `%s` where `%s`=?" % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

