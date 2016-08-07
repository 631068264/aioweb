#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/8/6 14:13
@annotation = '' 
"""
"""
Usage:
    rules = {
            'name': (8 < F_str('abc', 'default-xxx') < 32) & 'optional',
            'age': (10 < F_int() & 'optional' < 100),
            'choices': ((1 < F_int() < 10) & 'C' & 'required'
                & (lambda v: v % 2  0)),
            'email': ((2 < F_email(u'邮箱地址') < 32) & 'optional' & {
                    'default': u'%(name)s 正确格式是: xxxx@xxx.com',
                }),
            'url': (8 < F_str(u'链接', formatr'http://[\w./&?+~]+') < 1024) & 'optional',
        }
    fc = DataChecker(req, rules, err_msg_encoding='utf-8')
    fc.is_valid()
    fc.err_msg
    fc.raw_data
    fc.valid_data
"""
__all__ = [
    'F_str',
    'F_int',
    'F_float',
    'F_email',
    'F_mobile',
    'F_phone',
    'F_datetime',
]
default_encoding = 'utf8'
default_messages = {
    'json': 'json 格式错误',
    'multiple': '%(name)s 是数组',
    'max': '%(name)s 的最大值为%(max)s',
    'min': '%(name)s 最小值为%(min)s',
    'max_len': '%(name)s 最大长度为%(max_len)s个字符',
    'min_len': '%(name)s 最小长度为%(min_len)s个字符',
    'blank': '%(name)s 不能为空',
    'callback': '%(name)s 输入出错了',
    'format': '%(name)s 格式有错',
    'default': '%(name)s 格式有错',
}


class FieldInput(object):
    _type = None
    _min = None
    _max = None
    _optional = False
    _multiple = False
    _strict = False  # means empty string will treat as no input
    _attrs = ('optional', 'required', 'multiple', 'strict')

    _callbacks = (lambda v: (True, v),)
    _clean_data = None
    _raw_data = None
    _default_value = None

    _message_key = None

    def __init__(self, field_name=None, default_value=None):
        """
        :param field_name:
        :param default_value: can be a value or a func
        """
        self._messages = {}
        self._messages.update(default_messages)
        self._message_vars = {
            'name': field_name,
        }
        self._default_value = default_value

    def check_field(self, field_name, field_value):
        """

        :param field_name:
        :param field_value:
        :return: a tuple of 4 items:
            the first indicates if the value is valid
            the second is the raw data of user input
            the third is the valid data or, if not valid, is None
            the last is error message or, if valid, is None
        """
        if self._message_vars['name'] is None:
            self._message_vars['name'] = field_name
        if self._multiple:
            return self.check_multi(field_value)
        return self.check_value(field_value)

    def check_value(self, raw):
        """

        :param raw:
        if raw is None means  what the client send dose not include this field
         if raw == '' means the client send empty string
         when `strict' is specified, they are the same.
        :return:
        """
        valid, valid_data, message = False, None, None

        field_value = raw
        # check strict and _value
        if field_value is None or (field_value == '' and self._strict):
            if self._default_value is not None:
                if callable(self._default_value):
                    return True, raw, self._default_value(), None
                return True, raw, self._default_value, None
            else:
                field_value = None

        if field_value is not None:
            if isinstance(field_value, list):
                return False, raw, None, self._messages['multiple'] % self._message_vars
            elif isinstance(field_value, str):
                field_value = field_value.strip()
            valid, data = self._check_type(field_value)
            if valid:
                valid, data = self._callbacks[0](data)
                if valid:
                    valid_data = data
                else:
                    message = self._messages['callback']
            else:
                message = data

        # check optional
        elif self._optional:
            valid = True
            valid_data = field_value

        else:
            message = self._messages['blank']

        if message:
            message = message % self._message_vars

        return valid, raw, valid_data, message

    def check_multi(self, raws):
        if not raws and not self._optional:
            message = self._messages.get('blank') or self._messages['default']
            message = message % self._message_vars
            return False, raws, None, message

        valid_data = []
        for value in raws:
            valid, origin, valid_value, message = self.check_value(value)
            if not valid:
                return False, raws, None, message
            valid_data.append(valid_value)

        return True, raws, valid_data, None

    @property
    def multiple(self):
        return self._multiple

    def _check_type(self, value):
        raise NotImplementedError('you should use sub-class for checking')

    def _check_maxin(self, raw):
        value = len(raw) if isinstance(raw, str) else raw
        if self._max is not None and value > self._max:
            self._message_key = 'max_len' if isinstance(raw, str) else 'max'
            return False, self._messages[self._message_key]
        if self._min is not None and value < self._min:
            self._message_key = 'min_len' if isinstance(raw, str) else 'min'
            return False, self._messages[self._message_key]
        return True, ""

    # use & to connect
    def __and__(self, rule):
        if callable(rule):
            self._callbacks = (rule,)
        elif isinstance(rule, dict):
            self._messages.update(rule)
        elif rule in self._attrs:
            value = True
            if rule == 'required':
                rule = 'optional'
                value = False

            attr = '_%s' % rule
            if hasattr(self, attr):
                setattr(self, attr, value)
        else:
            raise NameError('%s is not support' % rule)

        return self

    def __lt__(self, max_value):
        self._max = max_value
        self._message_vars['max'] = max_value
        self._message_vars['max_len'] = max_value
        return self

    def __le__(self, max_value):
        raise NotImplementedError('"<=" is not supported now')

    def __gt__(self, min_value):
        self._min = min_value
        self._message_vars['min'] = min_value
        self._message_vars['min_len'] = min_value
        return self

    def __ge__(self, min_value):
        raise NotImplementedError('"=>" is not supported now')


class DataChecker(object):
    def __init__(self, request_data, rule, err_msg_encoding=default_encoding):
        """

        :param request_data: input data (dict object)
        :param rule: input rule
        :param err_msg_encoding:
        """
        self._req_data = request_data
        self._rule = rule
        self._encoding = err_msg_encoding
        self._checked = False

    def check(self):
        req_data = self._req_data
        rules = self._rule

        self._valid = True
        valid_data, raw_data, messages = {}, {}, {}

        for field, field_checker in rules.items():
            value = req_data.get(field, None)
            is_valid, raw_data[field], v, m = field_checker.check_field(field, value)
            if is_valid:
                valid_data[field] = v
            else:
                messages[field] = m
            self._valid = self._valid and is_valid

        self._raw_data = raw_data
        self._valid_data = valid_data
        self._messages = messages

        for field in self._messages:
            if not self._messages[field]:
                self._messages.pop(field)

        self._checked = True

    @property
    def err_msg(self):
        if not self._checked:
            self.check()
        return self._messages

    def is_valid(self):
        if not self._checked:
            self.check()
        return self._valid

    @property
    def raw_data(self):
        if not self._checked:
            self.check()
        return self._raw_data

    @property
    def valid_data(self):
        if not self._checked:
            self.check()
        return self._valid_data


class F_int(FieldInput):
    _strict = True

    def _check_type(self, value):
        try:
            value = int(value)
        except ValueError:
            return False, self._messages['default']

        is_ok, msg = self._check_maxin(value)
        if not is_ok:
            return False, msg

        return True, value


class F_float(FieldInput):
    _strict = True

    def _check_type(self, value):
        try:
            value = float(value)
        except ValueError:
            return False, self._messages['default']

        is_ok, msg = self._check_maxin(value)
        if not is_ok:
            return False, msg

        return True, value


class F_str(FieldInput):
    def __init__(self, field_name=None,
                 default_value=None, format=None):
        super(F_str, self).__init__(field_name, default_value)
        self._format = format

    def _check_type(self, value):
        is_ok, msg = self._check_maxin(value)
        if not is_ok:
            return False, msg

        if self._format:
            import re
            if not re.match(self._format, value):
                return False, self._messages['format']
        return True, value


class F_email(F_str):
    def _check_type(self, value):
        is_ok, msg = self._check_maxin(value)
        if not is_ok:
            return False, msg
        return self.is_email(value)

    def is_email(self, value):
        import re
        email = re.compile(r"^[\w.%+-]+@(?:[A-Z0-9-]+\.)+[A-Z]{2,4}$", re.I)
        if not email.match(value):
            return False, self._messages['default']
        return True, value


class F_phone(FieldInput):
    def _check_type(self, value):
        is_ok, msg = self._check_maxin(value)
        if not is_ok:
            return False, msg

        valid = value.replace('-', '').replace(' ', '').isdigit()
        if not valid:
            data = self._messages['default']
        else:
            data = value
        return valid, data


class F_mobile(FieldInput):
    def _check_type(self, value):
        valid = (value and
                 value.startswith('1') and
                 value.isdigit() and
                 len(value) == 11)
        if valid:
            data = value
        else:
            data = self._messages['default']
        return valid, data


class F_datetime(FieldInput):
    def __init__(self, field_name=None,
                 default_value=None, format='%Y-%m-%d %H:%M:%S'):
        super(F_datetime, self).__init__(field_name, default_value)
        self._format = format

    def _check_type(self, value):
        from datetime import datetime
        from time import strptime
        try:
            return True, datetime(*strptime(value, self._format)[0:6])
        except ValueError:
            return False, self._messages['format']
