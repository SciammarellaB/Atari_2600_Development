# Nove salas em 3 × 3, movimento em oito direções e tiro

Estudo para Atari 2600 com nove salas fixas conectadas, fundo preto, paredes
brancas e uma seta controlável. A barra cinza inferior mostra o número da sala
à esquerda e a amostra de texto `ATARI` centralizada. ROM de 4 KiB, NTSC,
sem bankswitching e sem som.

## Mapa e passagens

```text
1 — 2 — 3
|   |   |
4 — 5 — 6
|   |   |
7 — 8 — 9
```

O jogador começa na sala 5, no centro. Todas as salas vizinhas se conectam
por passagens no meio das respectivas paredes. As bordas externas do mapa
permanecem fechadas. Não há rolagem: ao mover contra uma passagem válida,
a sala é substituída e o personagem aparece na entrada oposta.

A posição no eixo perpendicular é preservada. As frações do movimento são
zeradas na troca, e o projétil da sala anterior é removido. Segurar o botão
permite um novo disparo a partir do quadro seguinte. Os projéteis permanecem
na sala atual e desaparecem no seu limite.

As aberturas norte/sul ocupam X=64..95. As aberturas oeste/leste ocupam
Y=28..51 na grade lógica da sala. A caixa inteira de 8 × 8 do personagem
precisa caber: seu canto superior esquerdo deve estar em X=64..88 para uma
travessia vertical, ou Y=28..44 para uma travessia horizontal. Encostar numa
borda fora desses intervalos continua bloqueando o movimento.

## Controles

Joystick 1 (setas do teclado na configuração padrão do Stella):

| Entrada | Ação |
| --- | --- |
| Esquerda / direita | Anda para o lado indicado e vira a seta |
| Cima / baixo | Anda para cima ou para baixo e vira a seta |
| Uma direção horizontal + uma vertical | Anda na diagonal e aponta para ela |
| Ctrl esquerdo ou Espaço / botão do joystick 1 | Atira na direção da seta |

A orientação muda imediatamente em passos de 45 graus. Soltar os controles
interrompe o movimento e mantém a orientação. Entradas opostas se anulam
por eixo. A velocidade é aproximadamente 0,5 pixel lógico por quadro,
com componentes diagonais normalizadas e posição fracionária 8.8.

O tiro nasce à frente da seta, captura sua orientação e segue reto, mesmo
quando o personagem vira. Mede 2 × 1 pixels lógicos (2 × 2 scanlines) e viaja
a 2 pixels lógicos por quadro, com diagonais normalizadas. Há um projétil
por vez; segurar o botão repete quando o anterior desaparece. Disparos que
nascem sobre uma parede são descartados no mesmo quadro.

## Geometria e HUD

A imagem tem 192 scanlines: 160 para a sala e 32 para o HUD. Cada sala usa
uma grade lógica de 160 × 80; uma linha lógica corresponde a duas scanlines.
A seta ocupa 8 × 8 pixels lógicos (8 × 16 scanlines). Começa em (76,36),
com o centro da caixa em (80,40).

As paredes laterais têm 4 pixels de largura: X=0..3 e X=156..159. As paredes
horizontais ocupam Y=0..3 e Y=76..79, com as passagens descritas acima.
O personagem fica limitado a X=4..148 e Y=4..68. O projétil fica em
X=4..154 e Y=4..75. Nenhum deles invade a barra inferior.

O HUD ocupa as scanlines 160..191 em cinza (`COLUBK=$06`). O número de sala
é uma fonte 3 × 7 desenhada pelo playfield em X=16..27. A palavra `ATARI`
usa fonte 5 × 7: cada linha é repetida duas vezes, totalizando 14 scanlines,
com 9 linhas cinzas acima e 9 abaixo. As letras começam em X=61,69,77,85,93,
ocupando 37 pixels de largura, com três pixels entre os desenhos das letras.

A amostra contém apenas os desenhos A/T/R/I e os dígitos 1..9. Ainda não é
um renderizador genérico de mensagens. Novos conteúdos exigem adaptar o
kernel e respeitar o orçamento de ciclos por linha.

## Montar e jogar

Na raiz do repositório, com DASM e Stella instalados:

```sh
make -C "Estudos/Movimentacao Tanque" check
make -C "Estudos/Movimentacao Tanque" run
```

`build` monta; `check` monta e verifica 4096 bytes e os três vetores;
`run` verifica e abre o Stella em NTSC com cartucho 4K. `DASM` e `STELLA`
permitem escolher executáveis existentes. Os artefatos ficam em
`build/main.bin`, `build/main.lst` e `build/main.sym`.

## Implementação

`CurrentRoom` guarda 0..8 na RAM, em ordem de leitura da grade; o HUD mostra
1..9. `RoomNorth/South/West/East` guardam os vizinhos na ROM, com `$FF` nas
bordas externas. `RoomDoors` usa os bits N=1, S=2, W=4 e E=8. `UpdateRoom`
consulta as saídas, aplica uma eventual troca e seleciona os ponteiros de
paredes e do dígito, durante a preparação do quadro.

O desenho usa tabelas compartilhadas de 80 faixas. As laterais podem apontar
independentemente para `RoomWallClosed` ou `RoomWallOpen`. Quatro tabelas PF2
cobrem as combinações de portas norte/sul. `CTRLPF=1` mantém a reflexão de
PF1/PF2; o kernel reescreve PF0 depois de sua parte esquerda, permitindo
portas diferentes nas duas laterais. Não há cópia de um mapa completo na RAM.

Para caber no tempo de cada scanline, `BuildPlayerBuffer` apaga as oito linhas
antigas da seta e escreve as oito novas antes do raster. `PlayerBuffer`
ocupa `$A0..$EF`; dois ponteiros ocupam `$F0..$F3`. A pilha dispõe de
`$F4..$FF` (12 bytes), suficiente para o fluxo atual, sem chamadas aninhadas.
`WallRest` reutiliza `EntryX` apenas no raster; `NextRoom` reutiliza
`ShotRowBefore` antes de `UpdateShot` prepará-lo.

As leituras das tabelas não cruzam páginas. Na primeira linha de cada par,
as escritas GRP1/PF0 esquerdo/GRP0/PF1/PF2/PF0 direito terminam nos ciclos
6/14/21/27/35/43; na segunda, em 3/11/18/24/32/40. Os NOPs e o alinhamento
das rotinas de posicionamento fazem parte da calibração horizontal.

A preparação reserva 8 linhas para controles, 8 para sala, 6 para tiro,
5 para o buffer, 3 para posicionar o projétil, 2 para o jogador, 4 de espera
e uma antes do raster: 37 no total. O quadro tem 3 linhas de sincronismo,
37 de preparação, 160 de cena, 32 de HUD e 30 de overscan: 262 linhas.

No HUD, Player 0 tem três cópias próximas (A/A/I), e Player 1 tem duas (T/R).
Os sprites são reposicionados sem `HMOVE`, evitando barras pretas sobre o
cinza. O dígito é escrito em PF1 antes de seu trecho esquerdo e apagado antes
da metade direita. Os modos NUSIZ voltam a zero na margem inferior para que
não apareçam cópias do personagem ou do tiro no quadro seguinte.

## Validação

Com a dependência opcional `py65` disponível no Python:

```sh
make -C "Estudos/Movimentacao Tanque" test
```

`check_tank.py` executa a ROM montada. Verifica movimento em oito direções,
frações, tiro, limites, as 24 conexões dirigidas, retorno, ausência de wrap,
bordas das passagens, diagonais e remoção do projétil na troca de sala.
Confere também as nove geometrias, o buffer da seta, o indicador de sala,
a referência visual independente de `ATARI`, as margens do HUD e os prazos
de escrita no TIA em quadros normais e em transições.

Os testes de CPU não simulam os pixels físicos do TIA nem substituem teste
em hardware. `main.asm` contém a implementação; `lab.py` e `Makefile` cuidam
da montagem/execução; `check_tank.py` valida a ROM. Nenhum outro estudo é
alterado.

A sala central foi conferida visualmente no Stella 6.7.1, com quatro
passagens abertas e o indicador 5 ao lado de ATARI. Captura local:
`build/salas-stella.png`.
