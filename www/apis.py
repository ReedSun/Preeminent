#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# page对象,用于储存分页信息
class Page(object):
    '''Page object for display pages.'''

    def __init__(self, item_count, page_index=1, page_size=10):  # page_index, page_size使用默认参数
        '''init Pagination by item_count, page_index, page_size
        item_count - 博客总数
        page_index - 页码
        page_size - 一个页面最多显示博客的数目'''
        self.item_count = item_count  # 从数据库中查询博客的总数获得
        self.page_size = page_size    # 可自定义,或使用默认值
        # 页面数目,由博客总数与每页的博客数共同决定
        # item_count 不能被page_size整除时,最后一页的博客数目不满page_size,但仍需独立设立一页
        # 以下式子等价与 math.ceil(item_count / page_size)
        self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
        # offset为偏移量,limit为限制数目,将被用于获取博客的api
        # 比如共有98篇博客,page_size=10, 则page_count=10.
        # 当前page_index=9,即这一页的博客序号(假设有)为81-90.此时offset=80
        if(item_count == 0) or (page_index > self.page_count):
            # 没有博客,或页码出错,将offset,limit置为0,页码置为1
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:  # 有博客,且指定页码并未超出页面总数的
            self.page_index = page_index  # 页码置为指定的页码
            self.offset = self.page_size * (page_index - 1)  # 设置页面偏移量
            self.limit = self.page_size  # 页面的博客限制数与页面大小一致
        self.has_next = self.page_index < self.page_count  # 页码小于页面总数,说有有下页
        self.has_previous = self.page_index > 1  # > 若页码大于1,说明有前页



# 几个简单的api错误异常类，用于抛出异常


'''
JSON API definition.
'''

import json, logging, inspect, functools

class APIError(Exception):
    '''
    the base APIError which contains error(required), data(optional) and message(optional).
    '''
    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message

class APIValueError(APIError):
    '''
    Indicate the input value has error or invalid. The data specifies the error field of input form.
    '''
    def __init__(self, field, message=''):
        super(APIValueError, self).__init__('value:invalid', field, message)

class APIResourceNotFoundError(APIError):
    '''
    Indicate the resource was not found. The data specifies the resource name.
    '''
    def __init__(self, field, message=''):
        super(APIResourceNotFoundError, self).__init__('value:notfound', field, message)

class APIPermissionError(APIError):
    '''
    Indicate the api has no permission.
    '''
    def __init__(self, message=''):
        super(APIPermissionError, self).__init__('permission:forbidden', 'permission', message)
