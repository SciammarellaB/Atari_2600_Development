#pragma once
#include <cstdint>
#include <cstring>
#include <cstddef>
#include <deque>
#include <string>
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define EXTERNAL 0
#define A0 54
#define A1 55
#define A2 56
#define A3 57
void digitalWrite(uint8_t,uint8_t);
void pinMode(uint8_t,uint8_t);
int digitalRead(uint8_t);
int analogRead(uint8_t);
void analogReference(uint8_t);
void delayMicroseconds(unsigned int);
void delay(unsigned long);
uint32_t millis();
struct FakeSerial {
  std::deque<uint8_t> input;
  std::string output;
  void begin(unsigned long) {}
  int available() {return int(input.size());}
  int read() {if(input.empty()) return -1;int b=input.front();input.pop_front();return b;}
  size_t write(uint8_t b) {output.push_back(char(b));return 1;}
};
extern FakeSerial Serial;
