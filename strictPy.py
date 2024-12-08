from typing import Any, Callable, Dict, List, Tuple, Union, get_type_hints, get_origin, get_args, Optional
from functools import wraps
import collections.abc


class StrictTypeError(TypeError):
    def __init__(self, message: str, method_name: str, param_name: str, received_type: type):
        self.message = f"{message} in method '{method_name}' for parameter '{param_name}'. Expected {type(received_type).__name__}, but got {received_type.__name__}."
        super().__init__(self.message)


class strictMeta(type):
    def __new__(cls, name, bases, dct):
        for attrName, attrValue in dct.items():
            if callable(attrValue) and not isinstance(attrValue, (staticmethod, classmethod)):
                dct[attrName] = cls._wrapMethod(attrValue)
        return super().__new__(cls, name, bases, dct)

    @staticmethod
    def _wrapMethod(method: Callable):
        methodHints = get_type_hints(method)

        @wraps(method)
        def wrapper(*args, **kwargs):
            argNames = method.__code__.co_varnames
            for idx, (argName, argValue) in enumerate(zip(argNames, args)):
                strictMeta._validateType(argName, argValue, methodHints, method.__name__)
            for kwargName, kwargValue in kwargs.items():
                strictMeta._validateType(kwargName, kwargValue, methodHints, method.__name__)

            result = method(*args, **kwargs)
            if "return" in methodHints:
                strictMeta._validateType("return value", result, methodHints, method.__name__)
            return result

        return wrapper

    @staticmethod
    def _validateType(name: str, value: Any, hints: Dict, method_name: str):
        expectedType = hints.get(name)
        if expectedType:
            originType = get_origin(expectedType)
            argsType = get_args(expectedType)

            # Handle nullable types (Optional)
            if isinstance(expectedType, Union) and type(None) in argsType:
                argsType.remove(type(None))  # Allow NoneType
                if value is None:
                    return

            # Validate Tuple, List, Dict
            if isinstance(value, collections.abc.Mapping):
                if originType is dict:
                    if not isinstance(value, dict):
                        raise StrictTypeError(f"'{name}' must be of type dict, but got {type(value).__name__}.", method_name, name, type(value))
                    key_type, value_type = argsType
                    for key, val in value.items():
                        if not isinstance(key, key_type):
                            raise StrictTypeError(f"Key in '{name}' must be of type {key_type.__name__}, but got {type(key).__name__}.", method_name, name, type(key))
                        if not isinstance(val, value_type):
                            raise StrictTypeError(f"Value in '{name}' must be of type {value_type.__name__}, but got {type(val).__name__}.", method_name, name, type(val))
                return

            elif isinstance(value, collections.abc.Sequence):
                if originType in {list, tuple}:
                    if not isinstance(value, originType):
                        raise StrictTypeError(f"'{name}' must be of type {originType.__name__}, but got {type(value).__name__}.", method_name, name, type(value))
                    if argsType:
                        for item in value:
                            if not isinstance(item, argsType[0]):
                                raise StrictTypeError(f"Items in '{name}' must be of type {argsType[0].__name__}, but got {type(item).__name__}.", method_name, name, type(item))
                return

            # For other cases, fall back to standard type checking
            if not isinstance(value, expectedType):
                raise StrictTypeError(f"'{name}' must be of type {expectedType.__name__}, but got {type(value).__name__}.", method_name, name, type(value))


class strictClass(metaclass=strictMeta):
    def __setattr__(self, name, value):
        classHints = get_type_hints(self.__class__)
        if name in classHints:
            strictMeta._validateType(name, value, classHints, self.__class__.__name__)
        super().__setattr__(name, value)


def strictFunction(func: Callable):
    funcHints = get_type_hints(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        argNames = func.__code__.co_varnames
        for idx, (argName, argValue) in enumerate(zip(argNames, args)):
            strictMeta._validateType(argName, argValue, funcHints, func.__name__)
        for kwargName, kwargValue in kwargs.items():
            strictMeta._validateType(kwargName, kwargValue, funcHints, func.__name__)

        result = func(*args, **kwargs)
        if "return" in funcHints:
            strictMeta._validateType("return value", result, funcHints, func.__name__)
        return result

    return wrapper
