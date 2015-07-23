CC=gcc
CFLAGS=-c -Wall -fPIC -I./include
LDFLAGS=-shared
SOURCES=src/libsample.c
OBJECTS=$(SOURCES:.c=.o)
EXECUTABLE=libsample.so

all: $(EXECUTABLE)

%.o: %.c
	$(CC) $(CFLAGS) $< -o $@

$(EXECUTABLE): $(OBJECTS) 
	$(CC) $(LDFLAGS) $(OBJECTS) -o $@


