#include <Arduino.h>

// 0: leitor direto de 5 V. 1: circuito LM339 + MOSFETs do manual.
// NUNCA use 1 na montagem direta: /CE e /OE mudam de polaridade no Mega.
#define PROGRAMMER_HARDWARE 1

const uint8_t AP[15] = {22,23,24,25,26,27,28,29,30,31,32,33,34,35,36};
// Mapeamento final padronizado; refaca as ligacoes conforme o manual.
const uint8_t RP[8] = {47,38,37,40,41,42,43,44};
const uint8_t WP[8] = {2,3,4,5,6,7,8,9};
const uint8_t CEP = 45, OEP = 46;
const uint32_t SIZE = 32768UL;
bool armed = false;

void ce(bool high) {
  digitalWrite(CEP, PROGRAMMER_HARDWARE ? !high : high);
}
void oe(bool high) {
  digitalWrite(OEP, PROGRAMMER_HARDWARE ? !high : high);
}
void releaseData() {
  if (PROGRAMMER_HARDWARE)
    for (uint8_t i=0; i<8; i++) digitalWrite(WP[i], LOW);
}
void idleBus() {
  ce(true); oe(true); releaseData();
}
void floatAddress() {
  for (uint8_t i=0; i<15; i++) {
    pinMode(AP[i], INPUT);
    digitalWrite(AP[i], LOW); // sem pull-up interno
  }
}
void address(uint16_t a) {
  for (uint8_t i=0; i<15; i++) {
    digitalWrite(AP[i], (a >> i) & 1);
    pinMode(AP[i], OUTPUT);
  }
}
uint8_t readByte(uint16_t a) {
  idleBus(); address(a);
  delayMicroseconds(20);
  ce(armed); // verify elevado: /CE=HIGH; leitura normal: LOW
  oe(false);
  delayMicroseconds(20); // inclui resposta dos comparadores
  uint8_t v=0;
  for (uint8_t i=0; i<8; i++)
    if (digitalRead(RP[i])) v |= uint8_t(1U << i);
  idleBus();
  return v;
}
uint32_t crcByte(uint32_t c, uint8_t b) {
  c ^= b;
  for (uint8_t i=0; i<8; i++)
    c = (c >> 1) ^ ((c & 1) ? 0xEDB88320UL : 0);
  return c;
}
void info() {
  Serial.println(PROGRAMMER_HARDWARE ?
    F("EPROM27 V1 PROGRAMMER") : F("EPROM27 V1 READER"));
}
void statistics() {
  uint32_t c=0xFFFFFFFFUL, ff=0, zz=0;
  for (uint32_t a=0; a<SIZE; a++) {
    uint8_t v=readByte(uint16_t(a));
    c=crcByte(c,v); ff+=(v==255); zz+=(v==0);
  }
  Serial.print(F("CRC32=")); Serial.print(c ^ 0xFFFFFFFFUL,HEX);
  Serial.print(F(" FF=")); Serial.print(ff);
  Serial.print(F(" ZERO=")); Serial.print(zz);
  Serial.println(ff==SIZE ? F(" BLANK") : F(" NOT_BLANK"));
}
void diagnose() {
  for (uint8_t i=0; i<3; i++) statistics();
  uint32_t errors=0; uint8_t mask=0;
  for (uint32_t a=0; a<SIZE; a++) {
    uint8_t x=readByte(uint16_t(a));
    readByte(uint16_t(a ^ 0x7FFFUL));
    uint8_t y=readByte(uint16_t(a));
    if (x!=y) {
      errors++; mask |= (x^y);
      if (errors<=12) {
        Serial.print(F("ADDR=")); Serial.print(a,HEX);
        Serial.print(F(" BEFORE=")); Serial.print(x,HEX);
        Serial.print(F(" AFTER=")); Serial.println(y,HEX);
      }
    }
  }
  Serial.print(F("DIFF=")); Serial.print(errors);
  Serial.print(F(" MASK=")); Serial.println(mask,HEX);
  Serial.println(F("END"));
}
void dump() {
  Serial.println(F("DATA 32768"));
  uint8_t block[128];
  for (uint32_t a=0; a<SIZE; a+=sizeof(block)) {
    for (uint8_t i=0; i<sizeof(block); i++)
      block[i]=readByte(uint16_t(a+i));
    Serial.write(block,sizeof(block));
  }
  Serial.println(); Serial.println(F("END"));
}
bool receive(uint8_t *p, uint16_t n) {
  uint32_t last=millis(); uint16_t k=0;
  while (k<n) {
    if (Serial.available()) { p[k++]=uint8_t(Serial.read()); last=millis(); }
    else if (uint32_t(millis()-last)>5000UL) return false;
  }
  return true;
}
void driveData(uint8_t v) {
  for (uint8_t i=0; i<8; i++)
    digitalWrite(WP[i], (v & (1U << i)) ? LOW : HIGH);
}
void interfaceTest() {
  if (!PROGRAMMER_HARDWARE || armed) {
    Serial.println(F("ERR HARDWARE_OR_ARMED")); return;
  }
  idleBus();
  const uint8_t pattern[4]={0x00,0xFF,0xAA,0x55};
  for (uint8_t k=0; k<4; k++) {
    driveData(pattern[k]); delayMicroseconds(50);
    uint8_t got=0;
    for (uint8_t i=0; i<8; i++)
      if (digitalRead(RP[i])) got |= uint8_t(1U << i);
    Serial.print(F("EXPECT=")); Serial.print(pattern[k],HEX);
    Serial.print(F(" GOT=")); Serial.println(got,HEX);
  }
  idleBus(); Serial.println(F("END"));
}
void programPulse(uint16_t a, uint8_t v, uint8_t ms) {
  idleBus(); address(a); driveData(v);
  delayMicroseconds(20);
  noInterrupts();
  ce(false);
  for (uint8_t i=0; i<ms; i++) delayMicroseconds(1000);
  ce(true);
  interrupts();
  delayMicroseconds(20); // hold dos dados apos /CE subir
  releaseData(); delayMicroseconds(20);
}
bool programByte(uint16_t a, uint8_t v) {
  uint8_t old=readByte(a);
  if ((old & v)!=v) return false; // exigiria mudar 0 para 1
  if (v==0xFF) return old==0xFF;
  for (uint8_t n=1; n<=25; n++) {
    programPulse(a,v,1);
    if (readByte(a)==v) {
      programPulse(a,v,uint8_t(3*n));
      return readByte(a)==v;
    }
  }
  return false;
}
void disarm() {
  idleBus(); armed=false; floatAddress();
}
void arm() {
  if (!PROGRAMMER_HARDWARE) { Serial.println(F("ERR HARDWARE")); return; }
  // Operador JA ajustou e mediu VCC=6 V e VPP=12.5 V.
  // Nao ha sensor nem controle automatico de tensao neste projeto.
  armed=true;
  for (uint32_t a=0; a<SIZE; a++) {
    if (readByte(uint16_t(a))!=0xFF) {
      disarm(); Serial.println(F("ERR NOT_BLANK")); return;
    }
  }
  Serial.println(F("ARMED"));
}
void writeBlock() {
  // W + endereco LE16 + tamanho U8 (1..128) + dados + CRC32 LE32.
  uint8_t h[3], data[128], tail[4];
  if (!receive(h,3)) { disarm(); Serial.println(F("ERR TIMEOUT")); return; }
  uint16_t a=uint16_t(h[0]) | (uint16_t(h[1])<<8);
  uint8_t n=h[2];
  if (!n || n>128 || uint32_t(a)+n>SIZE) {
    disarm(); Serial.println(F("ERR RANGE")); return;
  }
  if (!receive(data,n) || !receive(tail,4)) {
    disarm(); Serial.println(F("ERR TIMEOUT")); return;
  }
  uint32_t c=0xFFFFFFFFUL;
  for (uint8_t i=0; i<3; i++) c=crcByte(c,h[i]);
  for (uint8_t i=0; i<n; i++) c=crcByte(c,data[i]);
  c ^= 0xFFFFFFFFUL;
  uint32_t given=0;
  for (uint8_t i=0; i<4; i++) given |= uint32_t(tail[i]) << (8*i);
  if (c!=given) { disarm(); Serial.println(F("ERR CRC")); return; }
  if (!armed || !PROGRAMMER_HARDWARE) {
    Serial.println(F("ERR NOT_ARMED")); return;
  }
  for (uint8_t i=0; i<n; i++) {
    if (!programByte(uint16_t(a+i),data[i])) {
      disarm(); Serial.print(F("ERR VERIFY "));
      Serial.println(uint16_t(a+i),HEX); return;
    }
  }
  Serial.println(F("OK"));
}
void setup() {
  digitalWrite(CEP, PROGRAMMER_HARDWARE ? LOW : HIGH);
  digitalWrite(OEP, PROGRAMMER_HARDWARE ? LOW : HIGH);
  pinMode(CEP,OUTPUT); pinMode(OEP,OUTPUT);
  for (uint8_t i=0; i<8; i++) {
    pinMode(RP[i],INPUT);
    if (PROGRAMMER_HARDWARE) {
      digitalWrite(WP[i],LOW); pinMode(WP[i],OUTPUT);
    }
  }
  floatAddress(); idleBus();
  Serial.begin(115200); Serial.println(F("READY"));
}
void loop() {
  if (!Serial.available()) return;
  char cmd=char(Serial.read());
  if (cmd=='I') info();
  else if (cmd=='S') interfaceTest();
  else if (cmd=='D') { disarm(); Serial.println(F("DISARMED")); }
  else if (cmd=='A') arm();
  else if (cmd=='W') writeBlock();
  else if (cmd=='B' || cmd=='T' || cmd=='R') {
    if (armed) { Serial.println(F("ERR ARMED")); return; }
    if (cmd=='B') { statistics(); Serial.println(F("END")); }
    if (cmd=='T') diagnose();
    if (cmd=='R') dump();
    idleBus(); floatAddress();
  }
}
