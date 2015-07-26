#include "interface.h"
#include <stdio.h>

void foo()
{
	printf("foo\n");
}

void bar(four_bytes_t param)
{
	printf("bar, a: %i, b: %i\n", param.a, param.b);
}

const char* enum_to_string(enum some_enum e)
{
    switch (e)
    {
        case value_1:
            return "value 1";
        case value_2:
            return "value 2";
        case value_3:
            return "value_3";
        default:
            return "err";
    }
}