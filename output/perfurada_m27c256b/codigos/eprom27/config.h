#pragma once
// Calibracao EXCLUSIVA das medicoes: nao altera as tensoes fisicas das fontes.
// Ajustar um canal por vez: ganho_novo = ganho_atual * multimetro / tensao_P.
// Medir nos TPs, USB >=4,75 V, AREF fisica 2,500 V; nunca alimentar AREF com5V.
const float AREF_VOLTS=2.500f;
const float ADC_GAIN[4]={1.000f,1.000f,1.000f,1.000f}; // VCC,VPP,VIN_PROT,5B
const float ADC_SCALE[4]={5.0f,12.2f,12.2f,5.0f};
