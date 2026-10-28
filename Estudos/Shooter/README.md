# Shooter vertical — bombas, coletaveis, painel e estrelas

Estudo de um shooter para Atari 2600: nave azul-clara sobre um campo de
estrelas em movimento, movimento livre e tiro amarelo para cima.
ROM de 4 KiB, NTSC, sem bankswitching. Tem bombas e itens de teste caindo
periodicamente. Esta etapa ainda nao inclui inimigos, dano ou som.

## Montar e jogar

Na raiz do repositorio, com DASM e Stella instalados:

```sh
make -C Estudos/Shooter check
make -C Estudos/Shooter run
```

`build` monta a ROM; `check` tambem verifica tamanho e vetores; `run` verifica
e abre o Stella com NTSC e cartucho 4K. As saidas ficam em `build/main.bin`,
`build/main.lst` e `build/main.sym`. As variaveis `DASM` e `STELLA` permitem
selecionar outros executaveis instalados.

## Controles e comportamento

Use o joystick 1. No mapeamento padrao do Stella:

| Entrada | Acao |
| --- | --- |
| Setas | Move a nave para cima, baixo, esquerda e direita |
| Duas setas perpendiculares | Move na diagonal |
| Ctrl esquerdo / botao do joystick 1 | Dispara para cima |
| Botao de tiro segurado | Repete o tiro normal e, apos 1 segundo, tenta lancar uma bomba |
| Soltar o botao | Rearma a contagem da proxima bomba |

Soltar as direcoes interrompe o movimento. Direcoes opostas se anulam por
eixo. A nave permanece apontada para cima e fica inteiramente dentro da tela.
Ha um tiro normal por vez, alem da bomba. Ele nasce junto ao bico e conserva sua
coordenada horizontal enquanto sobe, mesmo que a nave se mova. Soltar o botao nao o apaga.

## Painel superior

O painel ocupa 24 scanlines no topo, com fundo azul-escuro, caracteres claros
3 x 7 e cada linha de fonte duplicada. Quatro linhas de margem superior e
quatro inferiores cercam as 14 linhas de texto. A linha 22 e um separador
cinza, e a linha 23 e um intervalo preto antes da cena.

Da esquerda para a direita: icone de nave e quantidade de vidas, seis
algarismos de pontuacao, icone de bomba e quantidade armazenada. A bomba e
o unico power-up armazenado; vida e velocidade do tiro sao
aplicadas imediatamente na coleta. O nivel de velocidade nao ocupa um slot no painel.

O estado inicial usa 3 vidas, zero bombas e pontuacao
`000000`. Os numeros sao lidos de variaveis reais: `Lives`, `BombCount` e os
tres bytes BCD `ScoreHi/ScoreMid/ScoreLo`. Pontuacao ainda nao e concedida,
pois nao existem inimigos. A renderizacao comporta seis digitos de pontos
e um digito para cada quantidade, com limite de 9 vidas e 9 bombas.

## Bombas e coletaveis de teste

Ha um item por vez. A primeira espera dura 120 quadros (2 segundos a 60 Hz),
e outra espera igual comeca quando o item e coletado, sai da tela ou e
removido pela explosao. Os tipos se alternam: bomba, vida, velocidade do tiro.
O item nasce em Y=0, no X da nave naquele instante, e segue reto para baixo
uma linha logica a cada dois quadros. A nave pode interceptar ou evitar o item.

| Tipo | Aparencia do item | Efeito ao encostar |
| --- | --- | --- |
| Bomba | Capsula larga, com intervalo no pavio | Soma uma bomba, ate 9 |
| Vida | Dois segmentos de largura media | Soma uma vida, ate 9 |
| Velocidade | Quatro segmentos estreitos | Aumenta a velocidade do tiro, ate tres melhorias |

Os itens sao cianos, desenhados pelo missile 0, com larguras de 8, 4 e 2
pixels respectivamente. A coleta usa caixas de 8 x 8 pixels logicos para
nave e item; e verificada depois do movimento do item. Um item no limite do
efeito tambem desaparece ao ser coletado. Nenhum item concede pontos nesta etapa.

Segurar o mesmo botao de tiro durante 60 quadros (1 segundo) faz uma tentativa
de lancamento: consome uma carga e cria um projetil amarelo de 8 x 4 pixels
logicos, acima do bico, subindo 4 linhas logicas por quadro. O tiro normal
continua. Ha uma bomba em voo por vez e uma tentativa por pressionamento.
Soltar rearma a contagem. Uma tentativa sem carga ou com outra bomba em voo
tambem exige soltar; coletar uma carga com o botao preso nao a gasta sozinho.

Ao sair pelo topo, a bomba acende o fundo da area de jogo por oito quadros,
um unico brilho por explosao. A explosao limpa os objetos existentes: bomba,
tiro normal e item em queda. A nave, o estoque, as vidas, os pontos e o
painel permanecem. O tiro normal pode recomecar no quadro seguinte enquanto
o botao estiver pressionado. Como ainda nao ha inimigos, nao ha alvos de
combate nem pontos por destruicao. `BlastPulse=1` sinaliza a explosao por um
quadro para a futura integracao dos inimigos.

## Fundo espacial

O fundo preto tem 24 estrelas cinzas distribuidas de forma diferente nas duas
metades da tela. Elas descem continuamente, inclusive com a nave parada, para
dar a sensacao de voo para a frente. Ao sair pelo rodape, reaparecem pelo
topo. A nave e o tiro aparecem sobre as estrelas, sem colisao com o fundo.

A rolagem avanca uma linha logica a cada quatro quadros. As estrelas ocupam
quatro pixels horizontais e uma ou duas linhas logicas. O mapa se repete a
cada 96 passos de rolagem; esta etapa usa uma unica velocidade de fundo.

## Geometria e implementacao

A cena abaixo do painel mede 160 x 84: cada linha corresponde a duas scanlines. A
nave tem 8 x 8 pixels logicos (8 x 16 scanlines), com inicio em (76,68).
Seu canto superior esquerdo fica em X=8..144 e Y=4..72. Move um pixel logico
por quadro em cada eixo acionado; diagonais combinam os dois deslocamentos.

O tiro mede 2 x 3 pixels logicos. Nasce em (X+3,Y-3), imediatamente acima
do bico, e sobe inicialmente 3 pixels logicos (6 scanlines) por quadro a partir do
quadro seguinte ao disparo. Cada melhoria aumenta um pixel por quadro:
velocidades de 3, 4, 5 e 6, mantidas em `ShotStep=3+ShotLevel`. Ao passar do
topo, desaparece; um novo tiro pode nascer no quadro seguinte se o botao continuar pressionado.

O Player 0 do TIA desenha a nave; o Player 1 desenha o tiro normal.
O missile 0 desenha o item; o missile 1 desenha a bomba. O sprite da nave
fica no centro de uma pagina de ROM cercado por zeros. `ShipPtr` aponta para
`ShipSprite-YPos`, e as 84 leituras indexadas retornam o desenho apenas nas
oito linhas ocupadas pela nave, sem cruzar paginas. Isso libera RAM para o
painel. O HUD usa 42 bytes em `$A0..$C9`, com seis registros por linha de
fonte, e oito ponteiros em `$CA..$D9`. A pilha fica em `$F0..$FF`.

O playfield desenha tanto o HUD quanto as estrelas, em faixas separadas.
`PrepareHud` seleciona os digitos BCD em quatro linhas e `BuildHud` combina
fontes de bits preordenados em 14 linhas durante o overscan, depois das
atualizacoes de bomba e coleta. O proximo quadro ja recebe os valores novos.
Os numeros e os icones ocupam as duas metades de forma independente.

Seis tabelas guardam PF0/PF1/PF2 para cada metade do campo de estrelas, sem
reflexao. Cada tabela tem duas copias do mapa vertical de 96 linhas e comeca
numa pagina da ROM; o indice `StarPhase+Y` fica em 0..178. A janela visivel
tem 84 linhas logicas. `StarTick` controla a velocidade e `StarPhase` diminui
circularmente. GRP1 conserva seu valor entre as duas scanlines da mesma faixa.

`PrepareEffects` seleciona janelas de ROM para os tiros e itens. Os flags
ficam em lacunas das fontes e das tabelas de estrelas. Fora dos desenhos,
as mascaras de bits retornam objetos apagados; os testes percorrem todas as
alturas para conferir essa separacao. O tiro normal usa apenas o bit 7 de P1,
com largura dobrada (`NUSIZ1=$35`), preservando os dois pixels de largura;
os bits altos desse mesmo registro deixam M1 com oito pixels. A rotina de
posicionamento compensa um pixel extra do player dobrado para manter o tiro
centralizado no bico. Os resets dos misseis recebem a compensacao oposta.

Os players persistem na segunda scanline de cada faixa. Os enables dos
misseis sao atualizados nessa segunda linha: o item fica deslocado uma
scanline para baixo e a bomba uma para cima, com corte no topo. Nenhum missile
aparece na faixa de texto do painel. O raster mantem todas as escritas do
playfield dentro dos prazos e termina a primeira linha no ciclo 75.

Cada quadro tem 3 linhas de VSYNC, 37 de preparacao, 24 de HUD, 168 de cena e
30 de overscan: 262 linhas. A preparacao usa uma linha para estrelas, 3 para
controles, 3 para tiro, uma para a janela da nave, 3 para efeitos, 2 para cada
um dos quatro posicionamentos, 17 de espera e uma para abrir a imagem.
O overscan usa 4 linhas para bomba, 5 para coleta, 4 para fontes do painel,
14 para seu buffer e 3 de espera. NOPs e alinhamentos fazem parte da
calibracao horizontal; nao os remova sem conferir os ciclos.

## Testes

A montagem e a execucao usam apenas a biblioteca padrao do Python. Para
executar os testes da ROM, instale a dependencia opcional em um ambiente local:

```sh
python3 -m venv Estudos/Shooter/build/venv
Estudos/Shooter/build/venv/bin/pip install -r Estudos/Shooter/requirements-dev.txt
make -C Estudos/Shooter test PYTHON=build/venv/bin/python
```

`check_shooter.py` executa o codigo montado no py65. Confere controles,
limites, origem e ciclo do tiro, janela da nave, pilha, 192 estados do HUD,
768 atualizacoes das estrelas e 252 janelas dos projeteis/itens. Verifica 985
quadros NTSC, com 24 linhas de HUD e 168 de cena, incluindo enable dos misseis,
todas as alturas dos itens, bomba/flash e os prazos do playfield.

`check_powerups.py` cobre limiares de 59/60/61 quadros, botao preso por 300
chamadas, soltura, falta de carga, bomba em voo, origem, movimento e detonacao,
limpeza da area, duracao do flash, espera/ciclo/saida dos itens, 867 combinacoes
de colisao, efeitos imediatos, limites de 9/9/3 e tiro normal durante a carga.
As rotinas de bomba e coleta tambem sao verificadas quanto aos slots fixos
de 4/5 WSYNC e balanceamento da pilha.

Os testes modelam RAM, entradas, flags e espera de WSYNC. Nao simulam os
pixels fisicos do TIA nem substituem a verificacao em emulador ou hardware.
