#include "interface.h"
#include <stdio.h>
#include <string.h>
#include <stdarg.h>

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

int buffer_copy(const void* source, void* dest, int count)
{
    memcpy(dest, source, count);
    return 0;
}

void pointer_to_pointer(char **arg)
{
    *arg = strdup("New pointer value");
}

void varargfunction(int count, ...)
{
    va_list list;
    va_start(list, count);

    while (count > 0) {
        printf("(%d) ", va_arg(list, int));
    }

    printf("\n");

    va_end(list);
}

