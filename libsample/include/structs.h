#ifndef LIBSAMPLE_STRUCTS_H
#define LIBSAMPLE_STRUCTS_H

#include "types.h"

struct three_bytes
{
    one_byte a;
    two_bytes b;
};

typedef struct three_bytes three_bytes_t;

typedef struct
{
    two_bytes a[2];
} four_bytes_t;

#endif
