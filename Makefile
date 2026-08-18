XENO_CONFIG := /usr/xenomai/bin/xeno-config

CFLAGS := $(shell $(XENO_CONFIG) --posix --alchemy --cflags 2>/dev/null)
LDFLAGS := $(shell $(XENO_CONFIG) --posix --alchemy --ldflags 2>/dev/null) -lm

CC := gcc
TARGET := latency_test
SRCS := latency_test.c

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CC) -O2 -Wall -o $@ $^ $(CFLAGS) $(LDFLAGS)

clean:
	rm -f $(TARGET) latency_data.csv latency_plot.png

.PHONY: all clean
