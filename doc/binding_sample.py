import ctypes

class CType:
    def __init__(self, t):
        self._type = t
        self._value = None 

    @property
    def type(self):
        return self._type

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, newvalue):
        self._value = newvalue

"""

struct three_bytes {
    unsigned char a;
    unsigned short b;
}

struct four_bytes_t {
    unsigned short a, b;

"""

class three_bytes:
    def __init__(self):
        self._a = CType(ctypes.c_uint8)
        self._b = CType(ctypes.c_ushort)

    @property
    def a(self):
        return self._a

    @property
    def b(self):
        return self._b

    @a.setter
    def a(self, value):
        self._a = value

    @b.setter
    def b(self, vaue):
        self._b = value

class four_bytes_t(ctypes.Structure):
    _fields_ = [("a", ctypes.c_ushort), ("b", ctypes.c_ushort)]


class libsample:
    def __init__(self, path):
        self._library = ctypes.CDLL(path)

    def foo(self):
        self._library.foo()

    def bar(self, p1):
        assert isinstance(p1, four_bytes_t), "wrong argument type"
        self._library.bar(p1)

# usage:
lib = libsample("/home/icek/Projects/binding/libsample/libsample.so")

lib.foo()

arg = four_bytes_t()
arg.a = 2
arg.b = 8
lib.bar(arg)

