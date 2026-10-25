#pragma once
#include <cstdint>
#include <deque>
#include <string>
#include <sstream>
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define HEX 16
#define F(s) s
void digitalWrite(uint8_t,uint8_t);
void pinMode(uint8_t,uint8_t);
int digitalRead(uint8_t);
void delayMicroseconds(unsigned int);
void delay(unsigned long);
uint32_t millis();
void noInterrupts();
void interrupts();
struct FakeSerial {
  std::deque<uint8_t> input;
  std::string output;
  void begin(unsigned long) {}
  int available() { return int(input.size()); }
  int read() { if(input.empty()) return -1; int b=input.front();input.pop_front();return b; }
  template<class T> void print(T v, int base=10) { std::ostringstream s; if(base==HEX) s<<std::hex; s<<+v; output+=s.str(); }
  void print(const char* v) { output+=v; }
  template<class T> void println(T v,int base=10) { print(v,base);println(); }
  void println() { output+="\r\n"; }
  size_t write(const uint8_t* p,size_t n) { output.append(reinterpret_cast<const char*>(p),n);return n; }
};
extern FakeSerial Serial;
