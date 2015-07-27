# pyautobind

## description
pyautobind is simple script for wrapping C-headers and libraries into python code. pyautobind will generate python definitions and ctypes code for your C library automatically. Just provide headers and let the pyautobind do the magic.

## dependencies
you need libclang and it's python bindings for this script to work correctly.

## WARNING
at this moment the script is in very unstable pre-beta stage. It may contain many severe BUGS. Please do not hesitate to report them directly to me or in project issue tracker.

## downsides
for now you need to know a little bit about ctypes python library as most of types on which pyautobind operates are in fact ctypes types. In future there will be some abstraction layer implemented (especially for arrays, buffers, strings, etc)

## example usage
for this example you can use provided stdio.cfg file. To generate python bindings just run following command, assume that you're in root of git repository:
`python src/main.py -i stdio.cfg -o stdio.py`
Please review stdio.cfg before running it, it shall contain path to stdio.h file in your system. If your stdio.h is located somewhere else you need to tune stdio.cfg file. Now the stdio.py file shall be generated. You can enter python shell and test generated (stdio.py) code:
```
$ python
Python 2.7.9 (default, Apr  2 2015, 15:33:21) 
[GCC 4.9.2] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import stdio
>>> lib = stdio.stdio("libc.so.6")
```
note that stdio.h is part of GNU C library, so you need to load it before executing anything from it.
```
>>> lib.printf("Hello %s\n", "world")
Hello world
12
```
"Hellow world" is what we want to print on stdio, 12 is return value from printf function, you can of course store it somewhere.
```
>>> ret = lib.printf("Hello world\n")
Hello world
>>> ret
12
```
You can now try to do something more "advanced", eg. file IO:
```
>>> fd = lib.fopen("beer.txt", "w")
>>> bottles = 99
>>> while bottles > 0:
...     ret = lib.fprintf(fd, "%i bottles of beer on the wall, %i bottles of beer.\n", bottles, bottles)
...     bottles = bottles - 1
...     if bottles > 0:
...             ret = lib.fprintf(fd, "Take one down and pass it around, %i bottles of beer on the wall.\n\n", bottles)
...     else:
...             ret = lib.fprintf(fd, "Take one down and pass it around, no more bottles of beer on the wall.\n")
...
>>> lib.fclose(fd)
0
```
Now you can check contents of beer.txt file. (now I feel that this software should be beerware :) )
