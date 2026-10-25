// Simulacao independente da API Arduino e da interface. Nao simula margens analogicas
// nem valida tempo real da AVR, contatos de reles, ADC real ou largura fisica de /CE.
#include "Arduino.h"
#include <array>
#include <vector>
#include <functional>
#include <stdexcept>
#include <iostream>
#include <cmath>
#define EPROM_HOST_TEST 1
FakeSerial Serial;
struct Pulse {uint16_t address;uint8_t value;uint64_t width;};
struct Environment {
  std::array<uint8_t,70> level{},mode{};
  std::array<uint8_t,32768> memory{};
  std::array<unsigned,32768> attempts{};
  std::vector<Pulse> pulses;
  uint64_t us=0,pulseStart=0,dataAt=0,addressAt=0;
  uint64_t serviceStart=0;
  uint64_t switchAt=0;
  std::vector<uint64_t> servicePulses;
  bool servicePending=false;
  bool key=false,stuckVpp=false,pending=false;
  float vin=12.0f,b5=5.0f,vccOffset=0;
  unsigned required=1,loweredWithVpp=0,badRead=0,k4HighWrites=0;
} env;
float supplyVcc() {
  return 4.2f+(env.level[10]?0:.25f)+(env.level[11]?0:1.0f)+(env.level[12]?0:.8f)+env.vccOffset;
}
float supplyVpp() {return env.stuckVpp || (env.level[14] && env.key && env.vin>=11)?12.75f:supplyVcc();}
uint16_t selected() {
  uint16_t a=0;for(unsigned i=0;i<15;i++) a|=uint16_t(env.level[22+i])<<i;return a;
}
uint8_t dataValue() {
  uint8_t v=0;for(unsigned i=0;i<8;i++) if(!env.level[2+i]) v|=1U<<i;return v;
}
void digitalWrite(uint8_t p,uint8_t v) {
  float before=supplyVcc();env.us++;
  if(p==14 && v==HIGH) env.k4HighWrites++;
  if(p>=2 && p<=9 && env.level[p]!=v) env.dataAt=env.us;
  if(p>=22 && p<=36 && env.level[p]!=v) env.addressAt=env.us;
  if(p==45 && env.level[p]!=v && supplyVpp()>10) {
    if(v==HIGH) {
      if(env.level[46]!=LOW || !env.level[49]) throw std::runtime_error("pulse OE/buffer invariant");
      if(env.us-env.dataAt<2 || env.us-env.addressAt<2) throw std::runtime_error("setup <2us");
      env.pending=true;env.pulseStart=env.us;
    } else if(env.pending) {
      uint16_t a=selected();uint8_t value=dataValue();uint64_t width=env.us-env.pulseStart;
      env.pulses.push_back({a,value,width});env.pending=false;
      if(++env.attempts[a]>=env.required) env.memory[a]&=value;
    }
  }
  if(p==45 && env.level[p]!=v && supplyVpp()<10 && !env.level[49]) {
    if(v==HIGH) {
      if(env.level[46]!=LOW) throw std::runtime_error("service OE not inactive");
      for(unsigned i=0;i<15;i++) if(env.mode[22+i]!=INPUT) throw std::runtime_error("service addresses not isolated");
      for(unsigned i=0;i<8;i++) if(env.level[2+i]) throw std::runtime_error("service data MOS active");
      env.servicePending=true;env.serviceStart=env.us;
    } else if(env.servicePending) {
      env.servicePulses.push_back(env.us-env.serviceStart);env.servicePending=false;
    }
  }
  env.level[p]=!!v;
  if((p==10 || p==11 || p==12) && env.stuckVpp && supplyVcc()<before-.01f) env.loweredWithVpp++;
}
void pinMode(uint8_t p,uint8_t m) {env.mode[p]=m;env.us++;}
int digitalRead(uint8_t p) {
  env.us++;
  if(p==48) {if(env.switchAt && env.us>=env.switchAt) env.key=true;return env.key?LOW:HIGH;}
  const uint8_t rp[8]={47,38,37,40,41,42,43,44};
  for(unsigned i=0;i<8;i++) if(p==rp[i]) {
    bool active=env.level[46]==HIGH && (supplyVpp()>10?env.level[45]==LOW:env.level[45]==HIGH);
    if(active) {
      if(!env.level[49]) throw std::runtime_error("read without address buffers");
      for(unsigned b=0;b<8;b++) if(env.level[2+b]) throw std::runtime_error("EPROM/MOS contention");
      return (env.memory[selected()]>>i)&1;
    }
    return !env.level[2+i];
  }
  throw std::runtime_error("unexpected digitalRead");
}
int analogRead(uint8_t p) {
  env.us+=110;
  float v[4]={supplyVcc(),supplyVpp(),env.vin,env.b5};
  float scale[4]={5,12.2f,12.2f,5};
  return int(std::lround(v[p-A0]/scale[p-A0]/2.5f*1023));
}
void analogReference(uint8_t r) {if(r!=EXTERNAL) throw std::runtime_error("wrong reference");}
void delayMicroseconds(unsigned int n) {env.us+=n;}
void delay(unsigned long n) {env.us+=1000*n;}
uint32_t millis() {env.us+=10;return uint32_t(env.us/1000);}
#include "../eprom27/eprom27.ino"

void require(bool ok,const char *why) {if(!ok) throw std::runtime_error(why);}
void reset() {
  env=Environment{};env.memory.fill(0xFF);Serial=FakeSerial{};
  connected=false;haveSequence=false;healthValid=false;serviceCalibration=false;stage=FAULT;nextAddress=0;lastError="BOOT";
  setup();require(stage==READ,"boot did not recover READ");
}
void handshake() {handle('I',0,nullptr,0);require(connected,"handshake failed");Serial.output.clear();}
void prepareProgram(unsigned required=1) {
  reset();handshake();env.key=true;env.required=required;
  require(enterProgram(),"arm failed");
}
void safe() {
  require(!env.level[49],"buffer still enabled");require(!env.level[14],"VPP still requested");
  require(!env.level[45] && !env.level[46],"controls still active");
  for(unsigned i=0;i<8;i++) require(!env.level[2+i],"data MOS still active");
  for(unsigned i=0;i<15;i++) require(env.mode[22+i]==INPUT,"addresses still driven");
}
std::vector<uint8_t> frame(uint8_t cmd,uint16_t sequence,const std::vector<uint8_t> &payload,bool corrupt=false) {
  std::vector<uint8_t> f={'E','2',cmd,uint8_t(sequence),uint8_t(sequence>>8),uint8_t(payload.size()),uint8_t(payload.size()>>8)};
  f.insert(f.end(),payload.begin(),payload.end());uint32_t c=0xFFFFFFFFUL;
  for(size_t i=2;i<f.size();i++) c=crcByte(c,f[i]);c^=0xFFFFFFFFUL;if(corrupt)c^=1;
  for(unsigned i=0;i<4;i++) f.push_back(uint8_t(c>>(8*i)));
  return f;
}
void receive(const std::vector<uint8_t> &f) {
  Serial.input.insert(Serial.input.end(),f.begin(),f.end());
  unsigned bound=0;while(Serial.available()) {receiveFrame();if(++bound>2000) throw std::runtime_error("parser hung");}
}
std::vector<uint8_t> block(uint16_t a,uint8_t n,uint8_t value) {
  std::vector<uint8_t> b={uint8_t(a),uint8_t(a>>8),n};b.insert(b.end(),n,value);return b;
}
int main() {
  unsigned passed=0;
  auto test=[&](const char *name,std::function<void()> f) {
    try {f();passed++;std::cout<<"PASS "<<name<<"\n";}
    catch(const std::exception &e) {std::cerr<<"FAIL "<<name<<": "<<e.what()<<"\n";exit(1);}
  };
  test("CRC32 independent known vector",[]{uint32_t c=0xFFFFFFFFUL;for(uint8_t b:std::string("123456789"))c=crcByte(c,b);require((c^0xFFFFFFFFUL)==0xCBF43926UL,"CRC32");});
  test("boot resets to maximum VCC then safe READ",[]{reset();safe();require(near(supplyVcc(),5,.01f),"wrong READ supply");});
  test("boot stuck VPP cannot lower VCC",[]{reset();env=Environment{};env.stuckVpp=true;stage=FAULT;setup();require(stage==FAULT,"stuck accepted");require(!env.loweredWithVpp,"lowered before VPP release");require(near(supplyVcc(),6.25f,.01f),"did not hold maximum");safe();});
  test("mode LER rejects arming without pulse",[]{reset();handshake();handle('A',1,nullptr,0);require(env.pulses.empty(),"pulsed");safe();});
  test("first attempt 100us no overpulse",[]{prepareProgram();require(programByte(0x1234,0xA5),"program rejected");require(env.pulses.size()==1,"overpulse present");require(env.pulses[0].width>=95 && env.pulses[0].width<=105,"wrong width intention");require(env.memory[0x1234]==0xA5,"wrong data");});
  test("25th attempt passes exactly25 pulses",[]{prepareProgram(25);require(programByte(32767,0x55),"25 failed");require(env.pulses.size()==25,"extra pulse");});
  test("26th needed fails after25",[]{prepareProgram(26);require(!programByte(0,0),"accepted");require(env.pulses.size()==25,"attempt count");});
  test("FF skip and 0to1 rejection without pulses",[]{prepareProgram();require(programByte(0,255),"FF rejected");env.memory[1]=0;require(!programByte(1,1),"0to1 accepted");require(env.pulses.empty(),"unexpected pulse");});
  test("mode removal aborts with isolated bus",[]{prepareProgram();env.key=false;require(!monitor(true),"mode accepted");require(!connected && stage==FAULT,"session retained");safe();});
  test("VIN undervoltage aborts without driving bus",[]{prepareProgram();env.vin=10.9f;require(!monitor(true),"VIN accepted");safe();});
  test("B5 overvoltage aborts",[]{prepareProgram();env.b5=5.08f;require(!monitor(true),"B5 accepted");safe();});
  test("VPP stuck on H holds6.25 and no drivers",[]{prepareProgram();nextAddress=SIZE;env.stuckVpp=true;handle('H',1,nullptr,0);require(stage==FAULT,"stuck ignored");require(!env.loweredWithVpp,"lowered VCC with VPP");require(near(supplyVcc(),6.25f,.01f),"VCC changed");safe();});
  test("wrong address blocks before program",[]{prepareProgram();auto b=block(1,1,0);handle('W',1,b.data(),b.size());require(env.pulses.empty(),"out-of-order write");safe();});
  test("CRC invalid rejects even nested W A bytes",[]{prepareProgram();auto b=block(0,4,'A');receive(frame('W',1,b,true));require(env.pulses.empty(),"CRC wrote data");require(!connected,"CRC left connected");safe();});
  test("partial frame timeout clears handshake",[]{prepareProgram();receive({'E','2','W',1,0,4,0,0});require(!connected,"timeout left connected");safe();});
  test("legacy W bytes cannot program",[]{prepareProgram();receive({'W',0,0,1,0,'A','D'});require(env.pulses.empty(),"legacy packet executed");});
  test("frame length132 rejected",[]{prepareProgram();receive(frame('W',1,std::vector<uint8_t>(132,0)));require(!connected && env.pulses.empty(),"oversize accepted");safe();});
  test("sequence mismatch aborts",[]{prepareProgram();auto b=block(0,1,0);handle('W',2,b.data(),b.size());require(env.pulses.empty(),"wrong seq wrote");safe();});
  test("reboot cannot retain handshake/programming",[]{prepareProgram();setup();connected=false;haveSequence=false;receive(frame('W',1,block(0,1,0)));require(env.pulses.empty(),"reboot write");safe();});
  test("session idle timeout returns safe READ rails",[]{prepareProgram();lastFrame=millis();env.us+=16000000;loop();require(stage==FAULT && !connected,"timeout ignored");safe();});
  test("full coverage gate on stages and final success",[]{prepareProgram();nextAddress=SIZE;require(enterVerify(VERIFY_HIGH),"H failed");require(near(supplyVcc(),6,.01f),"not6V");require(!env.level[14],"VPP high in final verify");require(!enterVerify(VERIFY_LOW),"skipped coverage");nextAddress=SIZE;require(enterVerify(VERIFY_LOW),"L failed");require(near(supplyVcc(),4.2f,.01f),"not4.2V");nextAddress=SIZE;require(enterVerify(VERIFY_FINAL),"F failed");require(near(supplyVcc(),5,.01f),"not5V");nextAddress=SIZE;handle('C',1,nullptr,0);require(stage==READ && Serial.output.find("SUCCESS")!=std::string::npos,"no success");safe();});
  test("final comparison mismatch prevents success",[]{prepareProgram();nextAddress=SIZE;require(enterVerify(VERIFY_HIGH),"H");auto b=block(0,1,0);handle('V',1,b.data(),b.size());require(stage==FAULT && !connected,"mismatch accepted");safe();});
  test("read range bounds and reply CRC",[]{reset();handshake();env.memory[32767]=0x5A;uint8_t p[4]={255,127,1,0};handle('R',1,p,4);require(Serial.output.size()==13,"reply size");require(uint8_t(Serial.output[8])==0x5A,"last address value");uint32_t c=0xFFFFFFFFUL,g=0;for(size_t i=2;i<9;i++)c=crcByte(c,uint8_t(Serial.output[i]));for(unsigned i=0;i<4;i++)g|=uint32_t(uint8_t(Serial.output[9+i]))<<(8*i);require((c^0xFFFFFFFFUL)==g,"reply CRC");safe();});
  test("stricter4.2V and5B voltage windows",[]{require(!suppliesOk({5,5,11.0f,5}),"VIN soft threshold");require(!suppliesOk({5,5,12,4.94f}),"B5 undervoltage");require(vccTolerance(4.2f)==.05f,"4.2V tolerance");});
  test("UV fault stays latched after supply returns",[]{prepareProgram();env.vin=10;monitor(true);env.vin=12;for(unsigned i=0;i<20;i++)loop();require(stage==FAULT && !connected,"automatic rearm after UV");safe();handle('I',0,nullptr,0);require(stage==READ && connected,"explicit recovery failed");safe();});
  test("P exposes ADC values even without handshake in FAULT",[]{reset();stage=FAULT;connected=false;handle('P',0,nullptr,0);require(Serial.output.size()==30,"wrong diagnostic frame length");require(uint8_t(Serial.output[8])==FAULT,"wrong diagnostic state");require(stage==FAULT && !connected,"diagnostic rearmed");safe();});
  test("CRC fault cannot execute subsequent valid W before I",[]{prepareProgram();receive(frame('W',1,block(0,1,0),true));receive(frame('W',1,block(0,1,0)));require(env.pulses.empty(),"post-error data executed");require(!connected,"post-error session rearmed");safe();});
  test("failed I invalidates old session and leaves P accessible",[]{prepareProgram();env.stuckVpp=true;handle('I',9,nullptr,0);require(stage==FAULT && !connected && !haveSequence,"old session kept after failed I");Serial.output.clear();handle('P',10,nullptr,0);require(Serial.output.size()==30,"P inaccessible after failed I");safe();});
  test("malformed I length aborts active session",[]{prepareProgram();uint8_t b=0;handle('I',9,&b,1);require(stage==FAULT && !connected,"malformed I left session active");safe();});
  test("end-to-end all32768 bytes W and three exact V passes",[]{
    prepareProgram();std::array<uint8_t,32768> image{};unsigned nonFF=0;
    for(unsigned a=0;a<image.size();a++){image[a]=uint8_t((a*73)^(a>>8));nonFF+=image[a]!=255;}
    uint16_t seq=1;
    auto pass=[&](char cmd){for(unsigned a=0;a<image.size();a+=128){auto b=block(a,128,0);for(unsigned i=0;i<128;i++)b[3+i]=image[a+i];handle(cmd,seq++,b.data(),b.size());require(connected && stage!=FAULT,"full block failed");}};
    pass('W');require(nextAddress==SIZE,"W coverage");require(env.memory==image,"wrong programmed image");require(env.pulses.size()==nonFF,"extra overprogram pulses");
    handle('H',seq++,nullptr,0);require(stage==VERIFY_HIGH,"high stage");pass('V');
    handle('L',seq++,nullptr,0);require(stage==VERIFY_LOW,"low stage");pass('V');
    handle('F',seq++,nullptr,0);require(stage==VERIFY_FINAL,"final stage");pass('V');
    handle('C',seq++,nullptr,0);require(stage==READ && Serial.output.find("SUCCESS")!=std::string::npos,"full cycle no success");safe();
  });
  test("K allfour modes never raises VPP or enables buffers",[]{
    for(uint8_t selection=0;selection<4;selection++) {
      reset();handshake();handle('K',1,&selection,1);
      const float expected[4]={5,6.25f,6,4.2f};
      require(near(supplyVcc(),expected[selection],.01f),"wrong K target");
      require(stage==FAULT && serviceCalibration && !connected,"K not service isolated");
      require(!env.k4HighWrites,"K energized K4");safe();
    }
  });
  test("K holds uncalibrated target for operator adjustment",[]{
    reset();env.vccOffset=.3f;uint8_t selection=3;handle('K',0,&selection,1);
    require(stage==FAULT && serviceCalibration,"K rejected uncalibrated target");
    require(Serial.output.find("UNCALIBRATED")!=std::string::npos,"missing uncalibrated reply");
    require(near(supplyVcc(),4.5f,.01f),"K reverted relay selection");
    for(unsigned i=0;i<20;i++)loop();require(near(supplyVcc(),4.5f,.01f),"cal target not held");
    require(!env.k4HighWrites,"K requested VPP");safe();
    env.vccOffset=0;Serial.output.clear();handle('Q',1,nullptr,0);
    require(Serial.output.find("PULSE_100US")!=std::string::npos,"Q after adjustment failed");
    require(env.servicePulses.size()==1,"not single service pulse");safe();
  });
  test("K and Q reject GRAVAR key",[]{
    reset();env.key=true;uint8_t selection=1;handle('K',0,&selection,1);
    require(!serviceCalibration && env.servicePulses.empty(),"K accepted GRAVAR");
    handle('Q',1,nullptr,0);require(env.servicePulses.empty(),"Q accepted GRAVAR");require(!env.k4HighWrites,"service requested K4");safe();
    reset();env.switchAt=env.us+250000;selection=3;handle('K',0,&selection,1);
    require(!serviceCalibration && near(supplyVcc(),5,.01f),"K selected after key changed while settling");safe();
  });
  test("K range and partial frame rejected",[]{
    reset();uint8_t selection=4;handle('K',0,&selection,1);require(!serviceCalibration,"K range4 accepted");safe();
    reset();receive({'E','2','K',0,0,1,0});require(!serviceCalibration,"partial K accepted");safe();
  });
  test("K VPP stuck cannot lower VCC",[]{
    reset();env.stuckVpp=true;uint8_t selection=3;handle('K',0,&selection,1);
    require(!serviceCalibration && !env.loweredWithVpp,"K lowered with VPP stuck");
    require(near(supplyVcc(),5,.01f),"K changed VCC before confirming VPP");safe();
  });
  test("Q READ single100us with isolated address bus",[]{
    reset();handle('Q',0,nullptr,0);
    require(env.servicePulses.size()==1,"missing single Q pulse");
    require(env.servicePulses[0]>=95 && env.servicePulses[0]<=105,"wrong Q pulse intention");
    require(env.pulses.empty() && !env.k4HighWrites,"Q became programming");safe();
  });
  test("Q refuses uncalibrated rails and nonservice fault",[]{
    reset();uint8_t selection=3;handle('K',0,&selection,1);env.vccOffset=.1f;handle('Q',1,nullptr,0);
    require(env.servicePulses.empty() && !serviceCalibration,"Q accepted bad target");safe();
    reset();stage=FAULT;lastError="VPP_STUCK";handle('Q',0,nullptr,0);
    require(env.servicePulses.empty(),"Q accepted unrelated fault");safe();
  });
  test("D exits calibration only after VPP follows",[]{
    reset();uint8_t selection=1;handle('K',0,&selection,1);handle('D',1,nullptr,0);
    require(stage==READ && !serviceCalibration && near(supplyVcc(),5,.01f),"D did not exit service");safe();
  });
  std::cout<<passed<<" tests passed; physical pulse/analog/relay validation NOT performed.\n";
}
