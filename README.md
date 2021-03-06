# pyautobind

## description
pyautobind is simple script for wrapping C-headers and libraries into python code. pyautobind will generate python definitions and ctypes code for your C library automatically. Just provide headers and let the pyautobind do the magic. **The script won't work with C++ libraries**.

## dependencies
you need libclang and it's python bindings for this script to work correctly. Generated script do not have any dependencies to external libraries, it uses only ctypes from Python.

## WARNING
at this moment the script is in very unstable pre-beta stage. It may contain many severe BUGS. Please do not hesitate to report them directly to me or in project issue tracker.

## downsides
for now you need to know a little bit about ctypes python library as most of types on which pyautobind operates are in fact ctypes types. In future there will be some abstraction layer implemented (especially for arrays, buffers, strings, etc)

## example usage
for this example you can use provided stdio.cfg file. To generate python bindings just run following command, assume that you're in root of git repository:
`python src/main.py -i configs/cstdlib.cfg -o cstdlib.py`
Please review stdio.cfg before running it, it shall contain path to stdio.h file in your system. If your stdio.h is located somewhere else you need to tune stdio.cfg file. Now the stdio.py file shall be generated. You can enter python shell and test generated (stdio.py) code:
```
$ python
Python 2.7.9 (default, Apr  2 2015, 15:33:21) 
[GCC 4.9.2] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import cstdlib
>>> lib = cstdlib.cstdlib("libc.so.6")
```
note that stdio.h is part of GNU C library, so you need to load it before executing anything from it.
```
>>> lib.stdio.printf("Hello %s\n", "world")
Hello world
12
```
"Hellow world" is what we want to print on stdio, 12 is return value from printf function, you can of course store it somewhere.
```
>>> ret = lib.stdio.printf("Hello world\n")
Hello world
>>> ret
12
```
You can now try to do something more "advanced", eg. file IO:
```
>>> fd = lib.stdio.fopen("beer.txt", "w")
>>> bottles = 99
>>> while bottles > 0:
...     ret = lib.stdio.fprintf(fd, "%i bottles of beer on the wall, %i bottles of beer.\n", bottles, bottles)
...     bottles = bottles - 1
...     if bottles > 0:
...             ret = lib.stdio.fprintf(fd, "Take one down and pass it around, %i bottles of beer on the wall.\n\n", bottles)
...     else:
...             ret = lib.stdio.fprintf(fd, "Take one down and pass it around, no more bottles of beer on the wall.\n")
...
>>> lib.stdio.fclose(fd)
0
```
Now you can check contents of beer.txt file. (now I feel that this software should be beerware :)) pyautobind will generate python classes for every C structure found in header files. You can check it out on libsample provided in this repository. It contains several structure definitions: `python src/main.py -i configs/libsample.cfg -o libsample.py`. Now you can open libsample.py:
```
...

class four_bytes(ctypes.Structure):                                                                              
        pass                                                                                                     

...                                                                                                    
                                                                                                                 
four_bytes._fields_ = [                                                                                          
        ("a", ctypes.c_ushort),                                                                                  
        ("b", ctypes.c_ushort),                                                                                  
        ]                                                                                                        
...
```
and sample session may look like this:
```
>>> import libsample
>>> lib = libsample.libsample("libsample/libsample.so")
>>> param = libsample.four_bytes(2, 7)
>>> lib.interface.bar(param)
bar, a: 2, b: 7
>>> param.a = 10
>>> lib.interface.bar(param)
bar, a: 10, b: 7
```
