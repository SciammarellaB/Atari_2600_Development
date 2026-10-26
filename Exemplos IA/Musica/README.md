# Laboratório de música — Atari 2600

Laboratório independente em Assembly 6507, com três músicas e menu para
escolher o áudio corrente. **3 TORIEL** toca a adaptação de **Heartache** e
começa automaticamente; **1 ESCALA** e **2 TENSAO** mantêm as experiências
anteriores; **0 MUDO** silencia os dois canais. A seta dourada à esquerda aponta para a seleção.

## Montar e executar

Requer Python 3, Make, DASM e Stella:

```sh
cd "/home/sciammarella/Fontes/Estudos/Atari_2600_Development/Exemplos IA/Musica"
make build
make run
```

A ROM fica em `build/main.bin`: 4096 bytes, NTSC, sem bankswitching.
`make run` monta antes de abrir o Stella com áudio habilitado. Pode definir
`DASM=/caminho/dasm` e `STELLA=/caminho/stella`. As configurações do emulador
ficam em `.tools/stella/`. Não há dependência dos outros exemplos.

## Controles

| Ação | Atari | Teclado padrão do Stella |
| --- | --- | --- |
| Opção anterior | Joystick 1: esquerda ou cima | ← / ↑ |
| Próxima opção | Joystick 1: direita ou baixo | → / ↓ |
| Próxima opção | Game Select | F1 |
| Reiniciar a opção atual | Botão de tiro | Espaço |
| Selecionar Heartache e reiniciar | Game Reset | F2 |

A ordem é **1 ESCALA → 2 TENSAO → 3 TORIEL → 0 MUDO → 1 ESCALA**. A seleção
muda o áudio imediatamente e reinicia a trilha escolhida. Tiro em MUDO
mantém o silêncio. Direções e botões exigem soltar e pressionar novamente;
não há repetição automática. Direções opostas são ignoradas. Reset tem
prioridade, seguido de Select, joystick e tiro. O menu permanece visível.

## Heartache — batalha da Toriel

A opção **3 TORIEL** adapta **Heartache**, de **Toby Fox**, da trilha de
[UNDERTALE](https://tobyfox.bandcamp.com/album/undertale-soundtrack).
A referência de notas e durações é a
[sequência MIDI de Revle, publicada no VGMusic](https://www.vgmusic.com/file/d56bcf22fbbf1c035d0065bd7d90334c.html).
Os créditos do compositor e do sequenciador são mantidos no JSON e nos dados gerados.

A ordem completa é reduzida para duas vozes, sem samples: uma melodia que
alterna as linhas principais da referência e um acompanhamento de baixo.
A introdução de arpejos é preservada. A redução seleciona a nota superior
da voz melódica e a inferior do baixo quando há acordes, ajusta oitavas e
quantiza entradas/saídas para passos de meio pulso do MIDI. Não reproduz a
orquestração completa da gravação original.

São **864 passos**, organizados em **72 blocos de 12**, com aproximadamente
**108,45 segundos por volta**. Passos alternam sete ou oito quadros por
acumulação fracionária, evitando a deriva de usar sempre sete ou oito.
Ao trocar de música ou apertar Fire, toda a posição, o andamento e os
ataques reiniciam; notas sustentadas não voltam a atacar a cada passo.

O TIA usa tons puros `AUDC=4` ou `AUDC=12`, escolhendo o divisor mais
próximo de cada nota. A melodia foi ajustada para Si♭4–Lá6 e o baixo para
Fá3–Mi4. O acompanhamento tem metade do volume da melodia. A afinação é
aproximada, conforme as frequências disponíveis no console.

Ouça a [prévia capturada no Stella](build/heartache-stella.wav), com cerca
de 24 segundos, em PCM16 mono a 48000 Hz. O WAV não é regenerado por
`make build`; a música completa continua na ROM.

`music/heartache.json` guarda os motivos e a ordem, em notas MIDI já
adaptadas; `null` é pausa e `-1` sustenta a nota anterior. O build gera
`build/heartache.inc` com as frequências, os ponteiros e os motivos
compartilhados para manter a ROM em 4K. O build é local e não baixa arquivos.
Edite o JSON ou o gerador, nunca o `.inc` gerado.

Para reproduzir opcionalmente a importação a partir do MIDI de referência:

```sh
python3 -m pip install --target .tools/python mido==1.3.3
PYTHONPATH=.tools/python python3 scripts/import_heartache.py /caminho/14_-_Heartache.mid
make build
```

O importador confere nomes das pistas e tempo, registra o SHA-256 da
referência e aplica a redução documentada. `mido` é necessário somente para
reimportar; a montagem normal usa apenas a biblioteca padrão do Python.

## Nova trilha: Tensão

Composição original para os dois canais do TIA, com quatro frases de
16 passos: apresentação do motivo, variação, contraste e retorno alterado.
A 60 Hz, cada passo dura 15 quadros: são colcheias a 120 BPM e um loop
completo de aproximadamente **16 segundos**.

- Canal 0: melodia de onda quadrada (`AUDC0=4`), com saltos, pausas,
  aproximações cromáticas e a quebra Sol–Sol♭ no motivo inicial.
- Canal 1: baixo pulsante (`AUDC1=6`), intercalado com pequenos ataques
  percussivos de ruído (`AUDC1=8`). São duas vozes simultâneas; baixo e
  percussão compartilham o segundo canal em momentos distintos.
- Os envelopes reduzem o volume depois do ataque. As pausas deixam espaço
  entre as frases e antes do retorno, sem interromper o menu.

A referência fornecida foi [este vídeo do YouTube](https://www.youtube.com/watch?v=28dbNKUz7QI).
Não foi possível reproduzir seu áudio no ambiente: esta versão é uma proposta
original de terror em 8 bits, sem transcrição, samples ou comparação auditiva
com a referência. As notas e o baixo usam as aproximações disponíveis no TIA.

A [prévia em WAV](build/tensao-stella.wav) contém cerca de 15,6 segundos
capturados da saída de áudio do Stella 6.7.1, convertidos para PCM16 mono
a 48000 Hz. É uma captura do emulador; `make build` não regenera esse WAV.

## Primeira trilha

Interpretação inicial do pedido, com quatro notas naturais ascendentes e
descida terminando em bemol:

**Dó4 – Ré4 – Mi4 – Fá4 → Mi4 – Ré4 – Dó4 – Si♭3 → pausa → repetir.**

São sete notas de 30 quadros (aproximadamente 0,5 s cada), um Si♭ de
60 quadros (1 s) e uma pausa de 45 quadros (0,75 s). A frase completa
leva cerca de 5,25 s a 60 Hz. As notas têm volume sustentado, uma redução
no final e uma pequena separação silenciosa. O Si♭ prolongado encerra a descida.

O canal 0 usa `AUDC0=12`, onda quadrada com divisão por seis. O canal 1
permanece silencioso, disponível para efeitos futuros. A afinação é aproximada:
o TIA não oferece todas as frequências da escala temperada. Para NTSC,
`f ≈ 31400 / (6 × (AUDF + 1))`:

| Nota pretendida | AUDF | Frequência aproximada |
| --- | --- | --- |
| Dó4 | 19 | 261,67 Hz |
| Ré4 | 17 | 290,74 Hz |
| Mi4 | 15 | 327,08 Hz |
| Fá4 | 14 | 348,89 Hz |
| Si♭3 | 21 | 237,88 Hz |

Essas alturas ficam a menos de 40 cents dos alvos. A última nota é o
Si♭ disponível nessa configuração do TIA; não é uma gravação de instrumento.

## Editar e acrescentar áudios

- `main.asm`: `UpdateMenu`, `RestartAudio` e `UpdateMusic` controlam a seleção
  e a reprodução. `Track` guarda 0 (silêncio), 1 (Escala), 2 (Tensão) ou 3 (Heartache).
- `Melody`: divisores das oito notas e da pausa final da Escala. Divisor menor sobe o tom.
- `Duration`: duração de cada passo em quadros.
- `Sustain` e `ReleaseEnd`: instantes de redução e corte do volume em cada passo.
  Mantenha `0 ≤ Sustain ≤ ReleaseEnd ≤ Duration`, com duração entre 1 e 255.
- `scripts/graphics.py`: fonte, textos, layout e indicador. `build/menu.inc`
  é gerado; não edite esse arquivo manualmente.
- `scripts/lab.py`: montagem, verificação estrutural e execução.
- `scripts/heartache.py`: validação do JSON, afinação e dados compactos de Heartache.
- `scripts/import_heartache.py`: importação opcional da referência MIDI.
- `music/heartache.json`: notas, motivos, ordem completa e créditos de Heartache.

- `TensionMelody`: 64 divisores da melodia nova; `$FF` representa pausa.
- `TensionBass`: 64 eventos do segundo canal: 0–31 para baixo, `$80` para
  percussão e `$FF` para silêncio.
- `LeadEnvelope`, `BassEnvelope` e `NoiseEnvelope`: 15 volumes por passo.
- `HeartBar`, `HeartPhase` e `HeartLength`: posição e duração fracionária de Heartache.
- `HeartAge0/HeartAge1`: envelopes independentes; `HeartPtr` aponta para o motivo atual.
- `CursorRows`: 48 bytes de RAM; VBLANK copia a máscara da opção atual.
  O kernel mantém as mesmas seis escritas de playfield por scanline.

Para adicionar outra trilha, acrescente as tabelas e o despacho em
`UpdateMusic`, amplie a navegação circular em `UpdateMenu`, os textos e
máscaras em `graphics.py` e `CursorLastRow`. Mantenha `RestartAudio` na troca
de seleção para zerar o passo e silenciar ambos os canais. Revise os testes.

## Validação

`make check` monta e confere tamanho e vetores da ROM. Para os testes de CPU,
instale a dependência opcional somente nesta pasta:

```sh
python3 -m pip install --target .tools/python py65==1.2.0
make test
```

Os testes executam as instruções da ROM e verificam 7.848 quadros com
3 linhas de VSYNC, 37 de VBLANK, 192 visíveis e 30 de overscan; playfield
48 × 4; navegação circular, entradas mantidas e prioridades; troca no fim da
trilha; duas voltas de cada música; envelopes e limites dos registradores;
baixo e percussão; silêncio em ambos os canais e quatro posições do indicador.
As versões anteriores do menu foram conferidas no Stella 6.7.1; as capturas
ficam em `build/screenshots/novo-menu/`. O WAV foi verificado quanto a duração e sinal
não silencioso; não houve avaliação auditiva. O modelo de testes não simula
pixels nem reproduz som. A afinação da Escala é
conferida pela fórmula, sem avaliação auditiva. Não foi testado em Atari
físico. O projeto está configurado para NTSC; PAL exige revisar frequências
e durações.

Heartache tem um oráculo independente que confere partitura, afinação,
ponteiros entre páginas, pausas, notas sustentadas e envelopes por canal,
em duas voltas naturais de 6.507 quadros cada. Todas as 16 combinações de
origem/destino do menu reiniciam a posição musical. A revisão independente
reproduziu a importação do MIDI e conferiu os 864 ataques: até 279 ciclos
por atualização, pilha mínima `$FB` e dados até `$FFC0`, sem sobreposição
com os vetores. O menu atual foi conferido no Stella 6.7.1 nas opções
Toriel e Tensão; a captura de Toriel fica em
`build/screenshots/heartache/heartache/main.png`.
A prévia de áudio tem sinal presente; não houve avaliação auditiva.

Referência técnica: [Stella Programmer's Guide, da Atari](https://www.atariage.com/2600/programming/2600_101/docs/stella.html),
seções de áudio e registradores `AUDC`, `AUDF` e `AUDV`.
