#ifndef LIBSAMPLE_TYPES_H
#define LIBSAMPLE_TYPES_H

#include <stdint.h>

typedef uint8_t one_byte;
typedef uint16_t two_bytes;

enum some_enum {
    value_1,
    value_2,
    value_3,
    value_4 = 10
};

typedef enum two_names_enum {
    foo_enum_value
} two_names_enum_t;

typedef enum {
    bar_enum_value
} unnamed_enum_t;

#endif

