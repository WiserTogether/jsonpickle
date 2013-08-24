"""
Custom handlers may be created to handle other objects. Each custom handler
must derive from :class:`jsonpickle.handlers.BaseHandler` and
implement ``flatten`` and ``restore``.

A handler can be bound to other types by calling :func:`jsonpickle.handlers.register`.

:class:`jsonpickle.customhandlers.SimpleReduceHandler` is suitable for handling
objects that implement the reduce protocol::

    from jsonpickle import handlers

    class MyCustomObject(handlers.BaseHandler):
        ...

        def __reduce__(self):
            return MyCustomObject, self._get_args()

    handlers.register(MyCustomObject, handlers.SimpleReduceHandler)

"""

import base64
import sys
import datetime
import time
import collections

from jsonpickle.compat import unicode


class Registry(object):

    def __init__(self):
        self._handlers = {}

    def register(self, cls, handler):
        """Register the a custom handler for a class

        :param cls: The custom object class to handle
        :param handler: The custom handler class

        """
        self._handlers[cls] = handler

    def get(self, cls):
        return self._handlers.get(cls)

registry = Registry()
register = registry.register
get = registry.get


class BaseHandler(object):

    def __init__(self, context):
        """
        Initialize a new handler to handle a registered type.

        :Parameters:
          - `context`: reference to pickler/unpickler

        """
        self.context = context

    def flatten(self, obj, data):
        """Flatten `obj` into a json-friendly form and write result in `data`"""
        raise NotImplementedError('You must implement flatten() in %s' %
                                  self.__class__)

    def restore(self, obj):
        """Restore the json-friendly `obj` to the registered type"""
        raise NotImplementedError('You must implement restore() in %s' %
                                  self.__class__)



class DatetimeHandler(BaseHandler):

    """Custom handler for datetime objects

    Datetime objects use __reduce__, and they generate binary strings encoding
    the payload. This handler encodes that payload to reconstruct the
    object.

    """
    def flatten(self, obj, data):
        pickler = self.context
        if not pickler.unpicklable:
            return unicode(obj)
        cls, args = obj.__reduce__()
        flatten = pickler.flatten
        args = [base64.b64encode(args[0])] + [flatten(i, reset=False) for i in args[1:]]
        data['__reduce__'] = (flatten(cls, reset=False), args)
        return data

    def restore(self, obj):
        cls, args = obj['__reduce__']
        value = base64.b64decode(args[0])
        unpickler = self.context
        restore = unpickler.restore
        cls = restore(cls, reset=False)
        params = (value,) + tuple([restore(i, reset=False) for i in args[1:]])
        return cls.__new__(cls, *params)

register(datetime.datetime, DatetimeHandler)
register(datetime.date, DatetimeHandler)
register(datetime.time, DatetimeHandler)


class SimpleReduceHandler(BaseHandler):
    """
    Follow the __reduce__ protocol to pickle an object. As long as the factory
    and its arguments are pickleable, this should pickle any object that
    implements the reduce protocol.
    """

    def flatten(self, obj, data):
        pickler = self.context
        if not pickler.unpicklable:
            return unicode(obj)
        flatten = pickler.flatten
        data['__reduce__'] = [flatten(i, reset=False) for i in obj.__reduce__()]
        return data

    def restore(self, obj):
        unpickler = self.context
        restore = unpickler.restore
        factory, args = [restore(i, reset=False) for i in obj['__reduce__']]
        return factory(*args)


register(time.struct_time, SimpleReduceHandler)
register(datetime.timedelta, SimpleReduceHandler)
if sys.version_info >= (2, 7):
    register(collections.OrderedDict, SimpleReduceHandler)
