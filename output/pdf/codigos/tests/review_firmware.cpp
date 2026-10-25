#include "Arduino.h"
#include <array>
#include <vector>
#include <iostream>
#include <stdexcept>
#include <functional>

FakeSerial Serial;
struct Pulse {uint16_t addr; uint8_t value; uint64_t duration;};
struct Environment {
  std::array<uint8_t,70> level{}, mode{};
  std::array<uint8_t,32768> memory{};
  std::array<unsigned,32768> attempts{};
  std::vector<Pulse> pulses;
  uint64_t time=0, start=0, rise=0, dataChanged=0, addressChanged=0;
  bool pending=false, checkHold=false, irq=true;
  unsigned required=1, reads=0, invalidVerify=0;
} env;
extern bool armed;
uint16_t selectedAddress() {uint16_t a=0;for(unsigned i=0;i<15;i++)a|=uint16_t(env.level[22+i])<<i;return a;}
uint8_t writtenData() {uint8_t v=0;for(unsigned i=0;i<8;i++)if(!env.level[2+i])v|=1U<<i;return v;}
void digitalWrite(uint8_t p,uint8_t v) {
  v=!!v;
  if(p>=2 && p<=9 && env.level[p]!=v) {
    if(env.checkHold && env.time-env.rise<2)throw std::runtime_error("data hold <2us");
    env.dataChanged=env.time;
  }
  if(p>=22 && p<=36 && env.level[p]!=v)env.addressChanged=env.time;
  if(p==45 && env.level[p]!=v && armed) {
    if(v==HIGH) { // MOS on: physical /CE falls
      if(env.level[46]!=LOW)throw std::runtime_error("/OE not HIGH at program start");
      if(env.time-env.dataChanged<2 || env.time-env.addressChanged<2)throw std::runtime_error("setup <2us");
      if(env.irq)throw std::runtime_error("interrupts enabled during pulse");
      env.start=env.time;env.pending=true;
    } else if(env.pending) {
      uint16_t a=selectedAddress();uint8_t value=writtenData();uint64_t width=env.time-env.start;
      env.pulses.push_back({a,value,width});
      if(width==1000 && ++env.attempts[a]>=env.required)env.memory[a]&=value;
      env.rise=env.time;env.checkHold=true;env.pending=false;
    }
  }
  env.level[p]=v;
}
void pinMode(uint8_t p,uint8_t m) {env.mode[p]=m;}
int digitalRead(uint8_t p) {
  static const uint8_t pins[]={47,38,37,40,41,42,43,44};
  for(unsigned bit=0;bit<8;bit++)if(p==pins[bit]) {
    env.reads++;
    // Physical /CE and /OE must be HIGH/LOW in elevated verify.
    if(armed && (env.level[45]!=LOW || env.level[46]!=HIGH))env.invalidVerify++;
    for(unsigned k=0;k<8;k++)if(env.level[2+k]!=LOW)throw std::runtime_error("data MOS not released during verify");
    return (env.memory[selectedAddress()]>>bit)&1;
  }
  throw std::runtime_error("unexpected digitalRead pin");
}
void delayMicroseconds(unsigned int t) {env.time+=t;}
void delay(unsigned long t) {env.time+=1000*t;}
uint32_t millis() {return uint32_t(env.time++/1000);}
void noInterrupts() {env.irq=false;}
void interrupts() {env.irq=true;}

#include "eprom27_programmer.ino"

void require(bool ok,const char* why) {if(!ok)throw std::runtime_error(why);}
void reset(unsigned required=1) {
  armed=false;env=Environment{};env.memory.fill(0xFF);env.required=required;Serial=FakeSerial{};
  setup();Serial.output.clear();armed=true;
}
void packet(uint16_t addr,const std::vector<uint8_t>& data,bool valid=true,uint8_t overrideLength=0xFF) {
  std::vector<uint8_t> p={uint8_t(addr),uint8_t(addr>>8),overrideLength==0xFF?uint8_t(data.size()):overrideLength};
  p.insert(p.end(),data.begin(),data.end());uint32_t c=0xFFFFFFFFUL;
  for(auto b:p)c=crcByte(c,b);c^=0xFFFFFFFFUL;if(!valid)c^=1;
  for(unsigned i=0;i<4;i++)p.push_back(uint8_t(c>>(8*i)));
  Serial.input.insert(Serial.input.end(),p.begin(),p.end());writeBlock();
}
void safeEnd() {
 require(env.level[45]==LOW && env.level[46]==LOW,"controls not inhibited");
 for(unsigned i=0;i<8;i++)require(env.level[2+i]==LOW,"data MOS active after operation");
 require(!env.invalidVerify,"wrong elevated verify mode");
}
int main() {
 unsigned passed=0;
 auto test=[&](const char* name,std::function<void()> f){try{f();passed++;std::cout<<"PASS "<<name<<"\n";}catch(const std::exception& e){std::cerr<<"FAIL "<<name<<": "<<e.what()<<"\n";exit(1);}};
 test("CRC32 vetor padrao independente 123456789",[]{uint32_t c=0xFFFFFFFFUL;for(uint8_t b:std::string("123456789"))c=crcByte(c,b);require((c^0xFFFFFFFFUL)==0xCBF43926UL,"CRC polynomial or convention");});
 test("sucesso primeira tentativa + sobrepulso 3ms + inversao dados",[]{reset();require(programByte(0x1234,0xA5),"rejected");require(env.pulses.size()==2,"pulse count");require(env.pulses[0].duration==1000 && env.pulses[1].duration==3000,"pulse widths");for(auto p:env.pulses)require(p.value==0xA5 && p.addr==0x1234,"wrong data/address");safeEnd();});
 test("sucesso tentativa 25 + sobrepulso 75ms",[]{reset(25);require(programByte(32767,0x55),"25 rejected");require(env.pulses.size()==26,"pulse count");require(env.pulses.back().duration==75000,"missing 75ms overpulse");require(env.attempts[32767]==25,"attempt count");safeEnd();});
 test("falha apos 25 sem sobrepulso",[]{reset(26);require(!programByte(0,0x00),"failure accepted");require(env.pulses.size()==25,"attempt count");for(auto p:env.pulses)require(p.duration==1000,"unexpected overpulse");safeEnd();});
 test("FF vazio nao recebe pulsos",[]{reset();require(programByte(0,0xFF),"FF rejected");require(env.pulses.empty(),"FF pulsed");safeEnd();});
 test("mudanca 0 para 1 rejeitada sem pulso",[]{reset();env.memory[0]=0;require(!programByte(0,0x01),"0->1 accepted");require(env.pulses.empty(),"invalid pulsed");safeEnd();});
 test("W CRC correto no endereco 32767",[]{reset();packet(32767,{0x5A});require(Serial.output=="OK\r\n","not OK");require(env.memory[32767]==0x5A,"wrong memory");safeEnd();});
 test("W bloco128 termina no endereco32767",[]{reset();packet(32640,std::vector<uint8_t>(128,0xA5));require(Serial.output=="OK\r\n","not OK");require(env.pulses.size()==256,"wrong block pulse count");for(unsigned a=32640;a<32768;a++)require(env.memory[a]==0xA5,"wrong block data");safeEnd();});
 test("W CRC errado rejeitado antes dos pulsos",[]{reset();packet(0,{0x00},false);require(Serial.output=="ERR CRC\r\n","CRC not rejected");require(!armed && env.pulses.empty(),"unsafe CRC failure");safeEnd();});
 test("W endereco32767 tamanho2 rejeitado",[]{reset();packet(32767,{0,0});require(Serial.output=="ERR RANGE\r\n","range accepted");require(!armed && env.pulses.empty(),"unsafe range failure");safeEnd();});
 test("W tamanho129 rejeitado",[]{reset();packet(0,std::vector<uint8_t>(129,0));require(Serial.output=="ERR RANGE\r\n","129 accepted");require(!armed && env.pulses.empty(),"unsafe length failure");safeEnd();});
 test("W tamanho0 rejeitado",[]{reset();packet(0,{});require(Serial.output=="ERR RANGE\r\n","0 accepted");require(!armed && env.pulses.empty(),"unsafe zero length");safeEnd();});
 test("W desarmado nao programa",[]{reset();disarm();packet(0,{0});require(Serial.output=="ERR NOT_ARMED\r\n","unarmed accepted");require(env.pulses.empty(),"unarmed pulsed");safeEnd();});
 test("W falha verify desarma e libera enderecos",[]{reset(26);packet(3,{0});require(Serial.output=="ERR VERIFY 3\r\n","wrong verify failure");require(!armed && env.pulses.size()==25,"unsafe verify failure");for(unsigned p=22;p<=36;p++)require(env.mode[p]==INPUT && env.level[p]==LOW,"address driven after failure");safeEnd();});
 test("D libera enderecos e inibe controles",[]{reset();address(0x7FFF);disarm();require(!armed,"still armed");for(unsigned p=22;p<=36;p++)require(env.mode[p]==INPUT && env.level[p]==LOW,"address not floated without pullup");safeEnd();});
 std::cout<<passed<<" testes passaram; verificacoes instrumentadas de setup, hold, modo verify e liberacao de dados.\n";
}
