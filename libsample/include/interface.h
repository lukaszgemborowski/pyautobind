#ifndef LIBSAMPLE_INTERFACE_H
#define LIBSAMPLE_INTERFACE_H

#include "structs.h"

void foo();
void bar(four_bytes_t param);
const char* enum_to_string(enum some_enum e);
int buffer_copy(const void* source, void* dest, int count);

#endif

