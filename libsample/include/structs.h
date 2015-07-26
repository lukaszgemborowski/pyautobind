#ifndef LIBSAMPLE_STRUCTS_H
#define LIBSAMPLE_STRUCTS_H

#include "types.h"

struct three_bytes
{
    one_byte a;
    two_bytes b;
};

typedef struct three_bytes three_bytes_t;

typedef struct four_bytes
{
    two_bytes a, b;
} four_bytes_t;

struct seven_bytes
{
	four_bytes_t a;
	struct three_bytes b;
};

struct combo
{
	int *pointer_to_integer;
	int integer_array[20];
};

#endif
