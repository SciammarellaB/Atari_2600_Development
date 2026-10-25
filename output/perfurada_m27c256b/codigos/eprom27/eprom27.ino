#include <Arduino.h>
#include "config.h"
#if defined(__AVR_ATmega2560__)
#include <avr/interrupt.h>
#elif !defined(EPROM_HOST_TEST)
#error "Este firmware exige Arduino Mega 2560 de 16 MHz."
#endif

// EXCLUSIVO da interface M27C256B com alimentacao integrada e SN74AHCT541N.
// Nao usar na montagem direta nem no gravador TS27C256Q antigo.
const uint8_t AP[15] = {22,23,24,25,26,27,28,29,30,31,32,33,34,35,36};
const uint8_t RP[8] = {47,38,37,40,41,42,43,44};
const uint8_t WP[8] = {2,3,4,5,6,7,8,9};
const uint8_t CEP=45, OEP=46, BUS_EN=49, MODE_PIN=48;
const uint8_t RELAY[4]={10,11,12,14};
const uint8_t LED_READ=50, LED_PGM=51, LED_FAULT=52;
const uint8_t LEDS[3]={LED_READ,LED_PGM,LED_FAULT};
const uint8_t SENSE[4]={A0,A1,A2,A3};
const uint32_t SIZE=32768UL;
const uint16_t SETTLE_MS=500, SETTLE_TIMEOUT_MS=2000;
const uint16_t HEALTH_PERIOD_MS=20, SESSION_TIMEOUT_MS=15000;
const uint16_t FRAME_TIMEOUT_MS=5000, BYTE_TIMEOUT_MS=1500;
const uint8_t MAX_PAYLOAD=131;

enum Stage:uint8_t { READ, PROGRAM, VERIFY_HIGH, VERIFY_LOW, VERIFY_FINAL, FAULT };
Stage stage=FAULT;
bool connected=false, haveSequence=false, healthValid=false;
bool serviceCalibration=false;
uint16_t nextSequence=0;
uint32_t nextAddress=0, lastFrame=0, lastHealth=0;
float targetVcc=6.25f;
struct Rails {float vcc,vpp,vin,b5;};
Rails measured={0,0,0,0};
uint16_t lastAdc[4]={0,0,0,0};
const char *lastError="BOOT";

uint32_t crcByte(uint32_t c,uint8_t b) {
  c^=b;
  for(uint8_t i=0;i<8;i++) c=(c>>1)^((c&1)?0xEDB88320UL:0);
  return c;
}
bool near(float x,float y,float tolerance) {return x>=y-tolerance && x<=y+tolerance;}
bool isSession() {return stage==PROGRAM || stage==VERIFY_HIGH || stage==VERIFY_LOW || stage==VERIFY_FINAL;}
void ce(bool high) {digitalWrite(CEP,high?LOW:HIGH);}
void oe(bool high) {digitalWrite(OEP,high?LOW:HIGH);}
void releaseData() {for(uint8_t i=0;i<8;i++) digitalWrite(WP[i],LOW);}
void idleBus() {ce(true);oe(true);releaseData();}
void floatAddress() {
  for(uint8_t i=0;i<15;i++) {pinMode(AP[i],INPUT);digitalWrite(AP[i],LOW);}
}
void isolate() {digitalWrite(BUS_EN,LOW);idleBus();floatAddress();}
void lights() {
  digitalWrite(LED_READ,stage==READ?HIGH:LOW);
  digitalWrite(LED_PGM,isSession()?HIGH:LOW);
  digitalWrite(LED_FAULT,stage==FAULT?HIGH:LOW);
}
Rails sampleRails() {
  float v[4];
  for(uint8_t ch=0;ch<4;ch++) {
    analogRead(SENSE[ch]); // descarte apos trocar o multiplexador
    uint16_t sum=0;
    for(uint8_t i=0;i<4;i++) sum+=analogRead(SENSE[ch]);
    lastAdc[ch]=(sum+2)/4;
    v[ch]=(float(sum)/4.0f)*(AREF_VOLTS/1023.0f)*ADC_SCALE[ch]*ADC_GAIN[ch];
  }
  measured={v[0],v[1],v[2],v[3]};return measured;
}
bool suppliesOk(const Rails &r) {return r.vin>=11.1f && r.vin<=13.0f && r.b5>=4.95f && r.b5<=5.05f;}
float vccTolerance(float target) {return target<4.5f?.05f:.10f;}
bool modeProgram() {return digitalRead(MODE_PIN)==LOW;}
void selectVcc(Stage s) {
  // Rele energizado HIGH curto-circuita o respectivo degrau do regulador.
  // Ordem de transicao somente com VPP seguindo VCC e barramento isolado.
  digitalWrite(RELAY[0],s==PROGRAM?LOW:HIGH);
  digitalWrite(RELAY[1],s==PROGRAM || s==VERIFY_HIGH?LOW:HIGH);
  digitalWrite(RELAY[2],s==VERIFY_LOW?HIGH:LOW);
  targetVcc=s==PROGRAM?6.25f:(s==VERIFY_HIGH?6.0f:(s==VERIFY_LOW?4.2f:5.0f));
}
bool waitRails(float vcc,bool highVpp,bool changingMode=false) {
  uint32_t start=millis();uint8_t good=0;
  while(uint32_t(millis()-start)<SETTLE_TIMEOUT_MS) {
    if(changingMode && !modeProgram()) {lastError="MODE";return false;}
    Rails r=sampleRails();
    bool ok=suppliesOk(r) && (vcc==0 || near(r.vcc,vcc,vccTolerance(vcc))) &&
      (highVpp?near(r.vpp,12.75f,.10f):near(r.vpp,r.vcc,.12f));
    // Alvo 0 serve para retirada de VPP/calibracao SEM chip. A fonte ainda
    // pode estar desajustada; nunca habilitar barramento somente por seguir.
    ok=ok && r.vcc>=(vcc==0?.5f:4.0f) && r.vcc<=(vcc==0?12.5f:6.5f);
    if(uint32_t(millis()-start)>=SETTLE_MS && ok) {
      if(++good>=8) {healthValid=false;return true;}
    } else good=0;
    delay(20);
  }
  lastError=highVpp?"VPP_TARGET":"RAIL_SETTLE";return false;
}
bool returnRead() {
  // NUNCA baixar VCC antes de confirmar que K4 retirou VPP elevada.
  serviceCalibration=false;isolate();digitalWrite(RELAY[3],LOW);
  if(!waitRails(0,false)) {
    if(measured.vpp>measured.vcc+.12f) lastError="VPP_STUCK";
    stage=FAULT;lights();return false;
  }
  selectVcc(READ);
  if(!waitRails(5.0f,false)) {stage=FAULT;lights();return false;}
  stage=READ;nextAddress=0;lights();return true;
}
void fail(const char *why) {
  // Tanto o barramento quanto a autorizacao de VPP sao retirados imediatamente.
  isolate();digitalWrite(RELAY[3],LOW);connected=false;haveSequence=false;
  bool recovered=returnRead();
  if(recovered) {stage=FAULT;lastError=why;lights();}
  // Em VPP_STUCK, manter o erro mais especifico e os degraus VCC inalterados.
}
bool monitor(bool force=false) {
  if(stage==FAULT) return false;
  if(isSession() && !modeProgram()) {fail("MODE");return false;}
  uint32_t now=millis();
  if(!force && healthValid && uint32_t(now-lastHealth)<HEALTH_PERIOD_MS) return true;
  Rails r=sampleRails();lastHealth=millis();healthValid=true;
  bool high=stage==PROGRAM;
  if(!suppliesOk(r) || !near(r.vcc,targetVcc,vccTolerance(targetVcc)) ||
     !(high?near(r.vpp,12.75f,.10f):near(r.vpp,r.vcc,.12f))) {
    fail("POWER");return false;
  }
  return true;
}
void address(uint16_t a) {
  for(uint8_t i=0;i<15;i++) {digitalWrite(AP[i],(a>>i)&1);pinMode(AP[i],OUTPUT);}
  digitalWrite(BUS_EN,HIGH);
}
bool readByte(uint16_t a,uint8_t &v) {
  if(!monitor()) return false;
  idleBus();address(a);delayMicroseconds(20);
  ce(stage==PROGRAM);oe(false);delayMicroseconds(20);
  v=0;
  for(uint8_t i=0;i<8;i++) if(digitalRead(RP[i])) v|=uint8_t(1U<<i);
  idleBus();return true;
}
void driveData(uint8_t v) {
  for(uint8_t i=0;i<8;i++) digitalWrite(WP[i],(v&(1U<<i))?LOW:HIGH);
}
void physicalPulse100us() {
#if defined(__AVR_ATmega2560__)
  static_assert(F_CPU==16000000UL,"Pulso calibrado para Mega 16 MHz");
  uint8_t saved=SREG;cli();
  // D45=PL4. Timer1 livre, clock/8: 0,5 us/tick. Preserva configuracao/contador.
  uint8_t savedA=TCCR1A,savedB=TCCR1B;
  uint16_t savedCount=TCNT1;
  TCCR1A=0;TCCR1B=_BV(CS11);TCNT1=0;
  PORTL|=_BV(PL4); // MOS ligado: /CE fisico LOW
  TCNT1=0;
  while(TCNT1<200) {}
  PORTL&=uint8_t(~_BV(PL4)); // MOS desligado: /CE sobe pelo pull-up
  TCCR1B=0;TCNT1=savedCount;TCCR1A=savedA;TCCR1B=savedB;SREG=saved;
#else
  // Stub verifica a intencao logica. Nao mede largura fisica nem RC do circuito.
  ce(false);delayMicroseconds(100);ce(true);
#endif
}
bool programPulse(uint16_t a,uint8_t v) {
  if(stage!=PROGRAM || !monitor()) return false;
  idleBus();address(a);driveData(v);delayMicroseconds(20);
  if(!modeProgram()) {fail("MODE");return false;}
  physicalPulse100us();delayMicroseconds(20);
  releaseData();delayMicroseconds(20);return true;
}
bool programByte(uint16_t a,uint8_t v) {
  uint8_t old;
  if(!readByte(a,old)) return false;
  if((old&v)!=v) {lastError="ZERO_TO_ONE";return false;}
  if(v==0xFF) return old==0xFF;
  for(uint8_t n=0;n<25;n++) {
    if(!programPulse(a,v) || !readByte(a,old)) return false;
    if(old==v) return true; // PRESTO II: nenhum sobrepulso
  }
  lastError="VERIFY_PROGRAM";return false;
}
bool enterProgram() {
  if(stage!=READ || !modeProgram()) {lastError="MODE_OR_STAGE";return false;}
  isolate();digitalWrite(RELAY[3],LOW);
  if(!waitRails(5,false,true)) return false;
  selectVcc(PROGRAM);
  if(!waitRails(6.25f,false,true)) return false;
  digitalWrite(RELAY[3],HIGH);
  if(!waitRails(6.25f,true,true)) return false;
  stage=PROGRAM;nextAddress=0;lights();
  for(uint32_t a=0;a<SIZE;a++) {
    uint8_t v;
    if(!readByte(uint16_t(a),v)) return false;
    if(v!=0xFF) {lastError="NOT_BLANK";return false;}
  }
  isolate();return true;
}
bool enterVerify(Stage next) {
  Stage wanted=next==VERIFY_HIGH?PROGRAM:(next==VERIFY_LOW?VERIFY_HIGH:VERIFY_LOW);
  if(stage!=wanted || nextAddress!=SIZE || !modeProgram()) {lastError="STAGE_OR_COVERAGE";return false;}
  isolate();digitalWrite(RELAY[3],LOW);
  if(!waitRails(targetVcc,false,true)) {
    if(measured.vpp>measured.vcc+.12f) lastError="VPP_STUCK";
    return false;
  }
  selectVcc(next);
  if(!waitRails(targetVcc,false,true)) return false;
  stage=next;nextAddress=0;lights();return true;
}
bool calibrateVcc(uint8_t selection,bool &calibrated) {
  // Servico SEM EPROM: deixa fontes selecionadas para ajuste do trimpot.
  // Nao exige o alvo ainda calibrado e nunca autoriza VPP de programacao.
  connected=false;haveSequence=false;serviceCalibration=false;
  isolate();digitalWrite(RELAY[3],LOW);
  if(modeProgram()) {lastError="SERVICE_KEY";return false;}
  if(!waitRails(0,false)) {
    if(measured.vpp>measured.vcc+.12f) lastError="VPP_STUCK";
    stage=FAULT;lights();return false;
  }
  if(modeProgram()) {lastError="SERVICE_KEY";stage=FAULT;lights();return false;}
  const Stage choices[4]={READ,PROGRAM,VERIFY_HIGH,VERIFY_LOW};
  selectVcc(choices[selection]);
  calibrated=waitRails(targetVcc,false);
  if(!calibrated && !waitRails(0,false)) {
    // Nem um erro de servico pode baixar VCC com VPP presa.
    if(measured.vpp>measured.vcc+.12f) lastError="VPP_STUCK";
    stage=FAULT;lights();return false;
  }
  if(modeProgram()) {lastError="SERVICE_KEY";stage=FAULT;lights();return false;}
  stage=FAULT;serviceCalibration=true;lastError="CALIBRATION";lights();return true;
}
bool servicePulse() {
  if(modeProgram() || !(stage==READ || (stage==FAULT && serviceCalibration))) {
    lastError="SERVICE_KEY_OR_STAGE";return false;
  }
  isolate();digitalWrite(RELAY[3],LOW);
  if(!waitRails(targetVcc,false)) {lastError="SERVICE_RAILS";return false;}
  if(modeProgram()) {lastError="SERVICE_KEY";return false;}
  // /OE HIGH, dados liberados e BUS_EN LOW durante TODO o pulso.
  // Esta operacao mede somente /CE: nao grava a EPROM e nao aplica12,75V.
  physicalPulse100us();idleBus();return true;
}

// Envelope: 'E','2',cmd,seqLE16,lenLE16,payload,CRC32LE de cmd..payload.
void response(uint8_t cmd,uint16_t seq,uint8_t status,const uint8_t *data,uint16_t n) {
  uint16_t length=n+1;
  uint8_t h[5]={cmd,uint8_t(seq),uint8_t(seq>>8),uint8_t(length),uint8_t(length>>8)};
  uint32_t c=0xFFFFFFFFUL;
  Serial.write(uint8_t('E'));Serial.write(uint8_t('2'));
  for(uint8_t b:h) {Serial.write(b);c=crcByte(c,b);}
  Serial.write(status);c=crcByte(c,status);
  for(uint16_t i=0;i<n;i++) {Serial.write(data[i]);c=crcByte(c,data[i]);}
  c^=0xFFFFFFFFUL;
  for(uint8_t i=0;i<4;i++) Serial.write(uint8_t(c>>(8*i)));
}
void answer(uint8_t cmd,uint16_t seq,const char *text,bool ok=true) {
  response(cmd,seq,ok?0:1,reinterpret_cast<const uint8_t*>(text),uint16_t(strlen(text)));
}
void commandError(uint8_t cmd,uint16_t seq,const char *why,bool abortSession=true) {
  if(abortSession) fail(why);
  answer(cmd,seq,lastError?lastError:why,false);
}
bool blockHeader(const uint8_t *data,uint16_t len,uint16_t &a,uint8_t &n) {
  if(len<4) return false;
  a=uint16_t(data[0])|(uint16_t(data[1])<<8);n=data[2];
  return n>0 && n<=128 && len==uint16_t(n)+3 && uint32_t(a)+n<=SIZE;
}
void handle(uint8_t cmd,uint16_t seq,const uint8_t *data,uint16_t len) {
  // D nunca arma VPP e e aceito mesmo apos erro de frame/perda de sessao.
  if(cmd=='D' && len==0) {
    if(connected) nextSequence=seq+1;
    if(returnRead()) answer(cmd,seq,"DISARMED");else commandError(cmd,seq,lastError);
    return;
  }
  if(cmd=='K') {
    if(len!=1 || data[0]>3) {commandError(cmd,seq,"SERVICE_RANGE");return;}
    bool calibrated=false;
    if(calibrateVcc(data[0],calibrated)) answer(cmd,seq,calibrated?"CALIBRATION":"UNCALIBRATED");
    else {stage=FAULT;lights();answer(cmd,seq,lastError,false);}
    return;
  }
  if(cmd=='Q') {
    if(len!=0) {commandError(cmd,seq,"LENGTH");return;}
    if(servicePulse()) {
      // Fora da sessao: nao avanca sequencia nem permite escrita aposQ.
      connected=false;haveSequence=false;answer(cmd,seq,"PULSE_100US");
    } else {
      serviceCalibration=false;connected=false;haveSequence=false;
      isolate();digitalWrite(RELAY[3],LOW);stage=FAULT;lights();
      answer(cmd,seq,lastError,false);
    }
    return;
  }
  // P e somente leitura e pode diagnosticar/calibrar ate um FAULT de partida.
  if(cmd=='P' && len==0) {
    if(connected && seq!=nextSequence) {commandError(cmd,seq,"SEQUENCE");return;}
    if(connected) nextSequence++;
    Rails r=sampleRails();uint8_t out[18]={uint8_t(stage),uint8_t(modeProgram())};
    float volts[4]={r.vcc,r.vpp,r.vin,r.b5};
    for(uint8_t i=0;i<4;i++) {
      uint16_t mv=uint16_t(volts[i]*1000+.5f);
      out[2+2*i]=uint8_t(mv);out[3+2*i]=uint8_t(mv>>8);
      out[10+2*i]=uint8_t(lastAdc[i]);out[11+2*i]=uint8_t(lastAdc[i]>>8);
    }
    response(cmd,seq,0,out,18);return;
  }
  if(cmd=='I') {
    if(len!=0) {commandError(cmd,seq,"LENGTH");return;}
    connected=false;haveSequence=false;
    if(!returnRead()) {answer(cmd,seq,lastError,false);return;}
    connected=true;haveSequence=true;nextSequence=seq+1;
    answer(cmd,seq,"EPROM27 V2 M27C256B_PRESTOII AUTO_RAILS MAX128");return;
  }
  if(!connected || !haveSequence) {answer(cmd,seq,"NEED_HANDSHAKE",false);return;}
  if(seq!=nextSequence) {commandError(cmd,seq,"SEQUENCE");return;}
  nextSequence++;lastFrame=millis();
  if(!monitor(true)) {answer(cmd,seq,lastError,false);return;}
  if(cmd=='A' && len==0) {
    if(enterProgram()) answer(cmd,seq,"ARMED");else commandError(cmd,seq,lastError);
  } else if(cmd=='H' || cmd=='L' || cmd=='F') {
    if(len!=0) {commandError(cmd,seq,"LENGTH");return;}
    Stage next=cmd=='H'?VERIFY_HIGH:(cmd=='L'?VERIFY_LOW:VERIFY_FINAL);
    if(enterVerify(next)) answer(cmd,seq,cmd=='H'?"VERIFY_6V":(cmd=='L'?"VERIFY_4V2":"VERIFY_5V"));
    else commandError(cmd,seq,lastError);
  } else if(cmd=='C' && len==0) {
    if(stage!=VERIFY_FINAL || nextAddress!=SIZE) {commandError(cmd,seq,"COVERAGE");return;}
    isolate();stage=READ;nextAddress=0;lights();answer(cmd,seq,"SUCCESS");
  } else if(cmd=='W' || cmd=='V') {
    uint16_t a;uint8_t n;
    if(!blockHeader(data,len,a,n)) {commandError(cmd,seq,"RANGE");return;}
    bool write=cmd=='W';
    if((write?stage!=PROGRAM:!(stage==VERIFY_HIGH || stage==VERIFY_LOW || stage==VERIFY_FINAL)) || a!=nextAddress) {
      commandError(cmd,seq,"STAGE_OR_ADDRESS");return;
    }
    for(uint8_t i=0;i<n;i++) {
      if(write) {
        if(!programByte(a+i,data[i+3])) {commandError(cmd,seq,lastError);return;}
      } else {
        uint8_t got;
        if(!readByte(a+i,got)) {answer(cmd,seq,lastError,false);return;}
        if(got!=data[i+3]) {commandError(cmd,seq,"VERIFY_IMAGE");return;}
      }
    }
    nextAddress+=n;isolate();answer(cmd,seq,"OK");
  } else if(cmd=='R' && len==4) {
    uint16_t a=uint16_t(data[0])|(uint16_t(data[1])<<8);
    uint16_t n=uint16_t(data[2])|(uint16_t(data[3])<<8);
    if(stage!=READ || !n || n>128 || uint32_t(a)+n>SIZE) {commandError(cmd,seq,"READ_RANGE_OR_STAGE");return;}
    uint8_t out[128];
    for(uint16_t i=0;i<n;i++) if(!readByte(a+i,out[i])) {answer(cmd,seq,lastError,false);return;}
    isolate();response(cmd,seq,0,out,n);
  } else if(cmd=='S' && len==0 && stage==READ) {
    uint8_t out[4];const uint8_t p[4]={0,255,170,85};idleBus();
    for(uint8_t k=0;k<4;k++) {
      if(!monitor()) {answer(cmd,seq,lastError,false);return;}
      driveData(p[k]);delayMicroseconds(50);out[k]=0;
      for(uint8_t i=0;i<8;i++) if(digitalRead(RP[i])) out[k]|=uint8_t(1U<<i);
    }
    isolate();response(cmd,seq,0,out,4);
  } else commandError(cmd,seq,"COMMAND_OR_LENGTH");
  lastFrame=millis();
}
bool serialByte(uint8_t &v,uint32_t frameStart) {
  uint32_t start=millis();
  while(!Serial.available()) {
    if(isSession() && !monitor()) return false;
    if(uint32_t(millis()-start)>BYTE_TIMEOUT_MS || uint32_t(millis()-frameStart)>FRAME_TIMEOUT_MS) return false;
  }
  if(uint32_t(millis()-frameStart)>FRAME_TIMEOUT_MS) return false;
  v=uint8_t(Serial.read());return true;
}
void receiveFrame() {
  static bool magicE=false;
  if(!Serial.available()) return;
  uint8_t b=uint8_t(Serial.read());
  if(!magicE) {magicE=b=='E';return;}
  magicE=false;
  if(b!='2') {magicE=b=='E';return;}
  uint32_t start=millis();uint8_t h[5],body[MAX_PAYLOAD],tail[4];
  for(uint8_t i=0;i<5;i++) if(!serialByte(h[i],start)) {fail("FRAME_TIMEOUT");return;}
  uint16_t seq=uint16_t(h[1])|(uint16_t(h[2])<<8);
  uint16_t n=uint16_t(h[3])|(uint16_t(h[4])<<8);
  if(n>MAX_PAYLOAD) {commandError(h[0],seq,"FRAME_LENGTH");return;}
  for(uint16_t i=0;i<n;i++) if(!serialByte(body[i],start)) {fail("FRAME_TIMEOUT");return;}
  for(uint8_t i=0;i<4;i++) if(!serialByte(tail[i],start)) {fail("FRAME_TIMEOUT");return;}
  uint32_t c=0xFFFFFFFFUL,given=0;
  for(uint8_t v:h) c=crcByte(c,v);
  for(uint16_t i=0;i<n;i++) c=crcByte(c,body[i]);
  for(uint8_t i=0;i<4;i++) given|=uint32_t(tail[i])<<(8*i);
  if((c^0xFFFFFFFFUL)!=given) {commandError(h[0],seq,"CRC");return;}
  handle(h[0],seq,body,n);
}
void setup() {
  // Nivel LOW antes de OUTPUT: todos os reles soltos, VCC maxima, VPP seguindo.
  digitalWrite(BUS_EN,LOW);pinMode(BUS_EN,OUTPUT);
  for(uint8_t p:RELAY) {digitalWrite(p,LOW);pinMode(p,OUTPUT);}
  digitalWrite(CEP,LOW);digitalWrite(OEP,LOW);pinMode(CEP,OUTPUT);pinMode(OEP,OUTPUT);
  for(uint8_t i=0;i<8;i++) {digitalWrite(WP[i],LOW);pinMode(WP[i],OUTPUT);pinMode(RP[i],INPUT);}
  pinMode(MODE_PIN,INPUT_PULLUP);
  for(uint8_t p:LEDS) {digitalWrite(p,LOW);pinMode(p,OUTPUT);}
  analogReference(EXTERNAL);isolate();Serial.begin(115200);
  // Se K4 estiver preso, returnRead NAO reduz VCC de 6,25 V.
  returnRead();lastFrame=millis();
}
void loop() {
  if(stage!=FAULT) monitor();
  if(isSession() && uint32_t(millis()-lastFrame)>SESSION_TIMEOUT_MS) fail("SESSION_TIMEOUT");
  receiveFrame();
}
