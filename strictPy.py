from typing import Any, Callable, Dict, List, Tuple, Union, get_type_hints, get_origin, get_args, Optional
from functools import wraps
import collections.abc

class StrictTypeError(TypeError):
    def __init__(self, message: str, method_name: str, param_name: str, received_type: type, value: Any, code: int):
        self.message = (
            f"[Error Code {code}] {message}\n"
            f"In method '{method_name}', parameter '{param_name}': "
            f"Expected {type.__name__}, but got {type(value).__name__} "
            f"with value '{value}'."
        )
        super().__init__(self.message)

class strictMeta(type):
    type_coercion_enabled = False
    range_validators = {}
    condition_validators = {}

    def __new__(cls, name, bases, dct):
        for attrName, attrValue in dct.items():
            if callable(attrValue) and not isinstance(attrValue, (staticmethod, classmethod)):
                dct[attrName] = cls._wrapMethod(attrValue)
        return super().__new__(cls, name, bases, dct)

    @staticmethod
    def enableTypeCoercion(enable: bool = True):
        strictMeta.type_coercion_enabled = enable

    @staticmethod
    def addRangeValidator(type_: type, min_value: Optional[int] = None, max_value: Optional[int] = None):
        strictMeta.range_validators[type_] = (min_value, max_value)

    @staticmethod
    def addConditionValidator(type_: type, condition: Callable[[Any], bool]):
        strictMeta.condition_validators[type_] = condition

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

            if strictMeta.type_coercion_enabled:
                try:
                    value = expectedType(value)
                except Exception:
                    pass

            if isinstance(value, collections.abc.Mapping):
                if originType is dict:
                    key_type, value_type = argsType
                    for key, val in value.items():
                        strictMeta._validateType(name, key, {name: key_type}, method_name)
                        strictMeta._validateType(name, val, {name: value_type}, method_name)
                return

            if isinstance(value, collections.abc.Sequence):
                if originType in {list, tuple}:
                    if argsType:
                        for item in value:
                            strictMeta._validateType(name, item, {name: argsType[0]}, method_name)
                return

            if expectedType in strictMeta.range_validators:
                min_value, max_value = strictMeta.range_validators[expectedType]
                if isinstance(value, (int, float)):
                    if min_value is not None and value < min_value:
                        raise StrictTypeError(
                            f"'{name}' must be greater than or equal to {min_value}.",
                            method_name,
                            name,
                            expectedType,
                            value,
                            code=105,
                        )
                    if max_value is not None and value > max_value:
                        raise StrictTypeError(
                            f"'{name}' must be less than or equal to {max_value}.",
                            method_name,
                            name,
                            expectedType,
                            value,
                            code=106,
                        )

            if expectedType in strictMeta.condition_validators:
                condition = strictMeta.condition_validators[expectedType]
                if not condition(value):
                    raise StrictTypeError(
                        f"'{name}' does not satisfy the condition.",
                        method_name,
                        name,
                        expectedType,
                        value,
                        code=107,
                    )

            if not isinstance(value, expectedType):
                raise StrictTypeError(
                    f"'{name}' must be of type {expectedType.__name__}.",
                    method_name,
                    name,
                    expectedType,
                    value,
                    code=104,
                )

class strictClass(metaclass=strictMeta):
    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise StrictTypeError(
                f"Cannot modify immutable attribute '{name}'",
                self.__class__.__name__,
                name,
                type(value),
                value,
                code=108,
            )
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
