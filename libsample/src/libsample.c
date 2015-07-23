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

