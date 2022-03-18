import functools
import inspect
import os
import pytest

__all__ = [
    "check",
    "equal",
    "not_equal",
    "is_",
    "is_not",
    "is_true",
    "is_false",
    "is_none",
    "is_not_none",
    "is_in",
    "is_not_in",
    "is_instance",
    "is_not_instance",
    "almost_equal",
    "not_almost_equal",
    "greater",
    "greater_equal",
    "less",
    "less_equal",
    "check_func",
    "raises",
]


_stop_on_fail = False
_failures = []


def clear_failures():
    global _failures
    _failures = []


def get_failures():
    return _failures


def set_stop_on_fail(stop_on_fail):
    global _stop_on_fail
    _stop_on_fail = stop_on_fail


class CheckContextManager(object):

    msg = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        __tracebackhide__ = True
        if exc_type is not None and issubclass(exc_type, AssertionError):
            if _stop_on_fail:
                self.msg = None
                return
            else:
                if self.msg is not None:
                    log_failure(self.msg)
                else:
                    log_failure(exc_val)
                self.msg = None
                return True
        self.msg = None

    def __call__(self, msg=None):
        self.msg = msg
        return self


check = CheckContextManager()


def check_func(func):
    @functools.wraps(func)
    def wrapper(*args, **kwds):
        __tracebackhide__ = True
        try:
            func(*args, **kwds)
            return True
        except AssertionError as e:
            if _stop_on_fail:
                raise e
            log_failure(e)
            return False

    return wrapper


@check_func
def equal(a, b, msg=""):
    assert a == b, msg


@check_func
def not_equal(a, b, msg=""):
    assert a != b, msg


@check_func
def is_(a, b, msg=""):
    assert a is b, msg


@check_func
def is_not(a, b, msg=""):
    assert a is not b, msg


@check_func
def is_true(x, msg=""):
    assert bool(x), msg


@check_func
def is_false(x, msg=""):
    assert not bool(x), msg


@check_func
def is_none(x, msg=""):
    assert x is None, msg


@check_func
def is_not_none(x, msg=""):
    assert x is not None, msg


@check_func
def is_in(a, b, msg=""):
    assert a in b, msg


@check_func
def is_not_in(a, b, msg=""):
    assert a not in b, msg


@check_func
def is_instance(a, b, msg=""):
    assert isinstance(a, b), msg


@check_func
def is_not_instance(a, b, msg=""):
    assert not isinstance(a, b), msg


@check_func
def almost_equal(a, b, rel=None, abs=None, msg=""):
    """
    for rel and abs tolerance, see:
    See https://docs.pytest.org/en/latest/builtin.html#pytest.approx
    """
    assert a == pytest.approx(b, rel, abs), msg


@check_func
def not_almost_equal(a, b, rel=None, abs=None, msg=""):
    """
    for rel and abs tolerance, see:
    See https://docs.pytest.org/en/latest/builtin.html#pytest.approx
    """
    assert a != pytest.approx(b, rel, abs), msg


@check_func
def greater(a, b, msg=""):
    assert a > b, msg


@check_func
def greater_equal(a, b, msg=""):
    assert a >= b, msg


@check_func
def less(a, b, msg=""):
    assert a < b, msg


@check_func
def less_equal(a, b, msg=""):
    assert a <= b, msg


def raises(*args, **kwargs):
    return CheckRaisesContext(*args, **kwargs)


class CheckRaisesContext:
    """
    TODO: docstring

    Within this context or when using as a called method, CheckRaisesContext
    will only catch one error, the first one, and return it.  It cannot resume
    control flow after an exception in the code being tested and accumulate
    other errors.  Use multiple calls to `raises` on subsections of that code
    that raise only one error apiece if you'd like to accomplish something like
    that.
    """

    def __init__(self, *expected_excs, msg=None):
        self.expected_excs = expected_excs
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        __tracebackhide__ = True
        # FIXME: DeMorgan-ize this.
        if exc_type is not None and issubclass(exc_type, self.expected_excs):
            self.msg = None
            return True
        else:
            # FIXME: why not `if not _stop_on_fail` and no return?
            if _stop_on_fail:
                # Returning something falsey here will cause the context
                # manager to *not* suppress an exception not in
                # `expected_excs`, thus allowing the higher-level Pytest
                # context to handle it like any other unhandle exception during
                # test execution, including display and tracebacks.
                self.msg = None
                return
            else:
                # FIXME: use `or` statement for `log_failure` to shorten
                if self.msg is not None:
                    log_failure(self.msg)
                else:
                    log_failure(exc_val)
                self.msg = None
                return True

    def __call__(self, callable_, *args, msg=None, **kwargs):
        self.msg = msg
        callable_(*args, **kwargs)

        return self


class DidNotRaiseException(Exception):
    pass


def get_full_context(level):
    (_, filename, line, funcname, contextlist) = inspect.stack()[level][0:5]
    filename = os.path.relpath(filename)
    context = contextlist[0].strip()
    return (filename, line, funcname, context)


def log_failure(msg):
    """
    Add a fail notice and "pseudo-traceback" to the global list of failures

    A pseudo-traceback looks like a traceback and is constructed similarly to
    one, but it only references client code, not library code.  We don't have
    full access to Pytest's traceback machinery here.
    """

    # TODO: Do I need this?  Could I rewrite to use `traceback` library, since
    # catching exceptions will give me a traceback object?

    __tracebackhide__ = True
    level = 3
    pseudo_trace = []
    func = ""
    while "test_" not in func:
        (file, line, func, context) = get_full_context(level)
        if "site-packages" in file:
            break
        line = "{}:{} in {}() -> {}".format(file, line, func, context)
        pseudo_trace.append(line)
        level += 1
    pseudo_trace_str = "\n".join(reversed(pseudo_trace))
    entry = "FAILURE: {}\n{}".format(msg if msg else "", pseudo_trace_str)
    _failures.append(entry)
