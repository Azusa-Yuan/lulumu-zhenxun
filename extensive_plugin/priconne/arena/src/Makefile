%.o: %.c
	gcc -c -O0 $^ -o $@ -fPIC
%.o: %.cpp
	g++ -c -O0 $^ -o $@ -fPIC
libpcrdwasm.so: pcrd.o main.o wasm-rt-impl.o
	g++ $^ --shared -o $@
all: libpcrdwasm.so
