# 01 — H.E.R.O.: voo, demolição e resgate

## Objetivo de estudo

Combinar movimento, gravidade, tiro, colisão com mapa, coleta e duas salas em
uma ROM de 4 KiB, mantendo os mecanismos do Atari visíveis no Assembly.
Leia `main.asm` na ordem: quadro e kernel; inicialização do jogo; regras;
preparação gráfica; posicionamento; bitmaps e mapas.

O resultado esperado é uma missão que começa na mina ocre e termina resgatando
o mineiro na galeria azul. Os dois cristais são opcionais. O herói e todos os
atores presentes aparecem em cada quadro de vídeo, inclusive depois do resultado.

## Coordenadas e geometria

X usa pixels de 0 a 159. A área da caverna usa Y de 0 a 87; cada unidade Y
corresponde a **duas linhas físicas**. Um personagem de oito bytes mede oito
pixels de largura e dezesseis linhas de altura. O painel fica acima da caverna,
portanto uma coordenada do jogo não inclui suas dezesseis linhas.

O playfield fornece vinte colunas na metade esquerda, espelhadas à direita.
Cada coluna ocupa quatro pixels. O mapa tem onze bandas verticais, cada uma
com oito unidades Y ou dezesseis linhas físicas. `Map1`/`Map2` são os bytes
de PF1/PF2 por banda; PF0 permanece em `$F0`, formando as margens.

| Elemento | Posição ou área, em coordenadas do jogo |
| --- | --- |
| Entrada de cada sala | Herói em `(24,8)` |
| Morcego | X=56..120, Y=16 |
| Parede removível | X=64..95, Y=24..47 |
| Plataforma superior | Y=32..39, abertura central na área da parede |
| Bateria | `(120,40)` |
| Cristal | `(56,64)` |
| Mineiro, somente na segunda sala | `(128,72)` |
| Poço para trocar de sala | Primeira sala, abertura central do piso Y=80 |

Na **primeira sala**, as plataformas inferiores ficam nas laterais. Depois da
parede, o eixo central permite descer até o poço. Para buscar o cristal, desça
abaixo da plataforma lateral antes de voar para a esquerda; depois retorne ao
centro. Cair pelo piso leva à sala azul, conservando energia, dinamites e cristais.

Na **segunda sala**, a plataforma inferior ocupa o centro, em Y=56..63, e o
piso é fechado. Saia do centro pela esquerda ou direita para descer. O cristal
fica sob essa plataforma: se já estiver no chão em Y=72, use o propulsor para
encostar nele por baixo. O mineiro fica à direita, sobre o piso.

## Como as regras se comportam

`Reset` limpa o TIA/RAM, prepara a pilha e configura entradas e tamanhos dos
mísseis. `NewGame` zera o resultado e os cristais, carrega 64 unidades de energia
e seis dinamites. `LoadRoom` posiciona o herói e cria os objetos da sala atual.

`UpdateGame` lê Game Reset e trata os resultados antes da lógica normal. Enquanto
se joga, avança o relógio, consome energia, move o herói e o morcego, atualiza o
laser e a bomba e verifica itens e contato inimigo. Nos estados finais, as regras
congelam, mas o kernel continua desenhando a cena. Um novo clique ou Game Reset
começa outra partida; manter o disparo pressionado não apaga o resultado.

`MoveHero` tenta um pixel horizontal por quadro. Cima tenta subir uma unidade Y
por quadro; soltar cima faz cair uma unidade Y a cada dois quadros. Não há
aceleração ou velocidade acumulada. Dois cantos da borda que avança são testados
antes de aceitar cada movimento; a borda traseira já estava em posição válida.

`SolidPoint` retorna Carry=1 se o ponto toca rocha e Carry=0 se está vazio.
No lado direito, converte X em `159-X` para consultar a metade espelhada. Divide
Y por oito, X por quatro e aplica `TileMasks`, respeitando a ordem invertida
dos bits de PF1 em relação a PF2. A mesma RAM alimenta imagem e colisão.

`MoveEnemy` desloca o morcego um pixel a cada quatro quadros, invertendo nos
extremos. Ele ocupa a faixa imediatamente acima da parede; seu caminho não
atravessa a rocha. O contato provoca derrota. Para atingi-lo, suba até alinhar
o capacete à sua altura e use o laser.

`UpdateLaser` captura `Facing` no disparo. Virar o herói depois não muda a
trajetória. O laser mede oito pixels por duas linhas e anda três pixels por
quadro, para a esquerda ou direita. Rocha comum o absorve; o morcego morre com
um acerto. Oito impactos na região da parede chamam `DestroyWall`, fornecendo
uma alternativa à dinamite.

`UpdateBomb` exige chão abaixo do centro do herói, estoque e um novo comando
de baixo. Registra `BombX`/`BombY`, gasta uma dinamite e inicia sessenta quadros
de pavio. Ao terminar, toca ruído, produz um clarão e destrói uma parede próxima.
A explosão também derrota o herói quando a distância está nos intervalos
X=-15..15 e Y=-11..11 em relação à posição plantada. Recuar mais de quinze
pixels horizontalmente já escapa desse retângulo.

`DestroyWall` remove os bits altos de PF2 nas bandas 3, 4 e 5. A mudança vale
imediatamente tanto para o desenho quanto para `SolidPoint`. As rochas fixas
dos bits baixos permanecem. Cada sala começa com sua própria parede.

`CollectItems` testa retângulos de oito por oito unidades. A bateria recupera
24 unidades, com limite de 64; o cristal incrementa `Gems`. As flags
`FuelAlive` e `GemAlive` impedem coleta repetida. Encostar no mineiro na sala 1
define `State=Won`; energia zero, explosão próxima ou morcego definem `Lost`.
Cristais não são requisito para concluir o resgate.

`StartSound` usa apenas um canal: A escolhe a forma de onda, X a frequência e
Y a duração. O efeito mais recente substitui o anterior. `SoundClock` continua
decrementando no resultado, permitindo silenciar o canal ao terminar o efeito.

## Sprites sem flicker

O Atari possui somente dois players. P0 permanece com o herói; P1 é reutilizado
em faixas verticais separadas. Isso permite desenhar todos os objetos presentes
**no mesmo quadro**, sem selecionar um ator diferente a cada quadro.

| Objeto de P1 | Pares de desenho | Reposicionamento anterior |
| --- | --- | --- |
| Morcego | 16..23 | VBLANK, antes da área visível |
| Bateria | 40..47 | Segunda linha do par 29 |
| Cristal | 64..71 | Segunda linha do par 59 |
| Mineiro | 72..79 | Segunda linha do par 71 |

As últimas linhas dos bitmaps de morcego, bateria e cristal são zero. Para a
troca cristal/mineiro, o par 71 vazio oferece a janela de reposicionamento.
O primeiro byte do mineiro é antecipado em `FirstActorPixel`: sem isso, seu
capacete perderia a primeira linha por causa do caminho especial do kernel.

`KernelEvents` agenda as preparações de ponteiro/cor e os resets de P1.
`HMCLR` zera os ajustes de todos os objetos antes das trocas; cada reset seguinte
grava somente HMP1. Assim, os HMOVE posteriores não deslocam novamente o herói,
o laser ou a bomba. A agenda supõe que as bandas 8 e 9 tenham o mesmo mapa,
pois o evento do mineiro substitui a recarga normal dessa banda.

M0 desenha o laser. M1 desenha a pequena carga de dinamite junto aos pés de quem
a plantou; seu posicionamento ocorre no VBLANK e sua habilitação no kernel.
Não é preciso disputar P1 com o morcego ou o mineiro durante o pavio.

Os bitmaps são bytes binários: bit 7 à esquerda, bit 0 à direita. Um bit 1
acende um pixel na cor do objeto. `REFP0=8` espelha o herói quando olha para a
esquerda. `PrepareGraphics` alterna o primeiro byte da hélice a cada quatro
quadros; os demais bytes do corpo permanecem iguais.

`HeroColors` fornece uma cor NTSC por linha do bitmap: hélice clara, eixo
cinza, capacete amarelo, rosto, uniforme azul e botas escuras. O kernel escreve
`COLUP0` antes dos pixels e conserva a cor nas duas linhas físicas do par.
`NextHeroRow` guarda o índice 0..7; o índice 8 seleciona uma linha transparente
e a cor padrão do laser. P0 e M0 compartilham `COLUP0`: quando o laser está na
mesma altura de uma parte do herói, recebe a cor daquela faixa. Cada linha do
personagem continua usando uma única cor; não há cores diferentes lado a lado.

## Quadro e orçamento de ciclos

`Frame` gera três linhas de VSYNC e usa o RIOT para completar 37 linhas de
VBLANK, incluindo preparação gráfica e quatro posicionamentos horizontais.
O painel ocupa dezesseis linhas; sua última linha também prepara a entrada
da caverna e assume suas cores/margens. O kernel desenha 88 pares, totalizando
176 linhas. O overscan reserva trinta linhas para a lógica. Total:
`3 + 37 + 16 + 176 + 30 = 262` linhas por quadro NTSC.

Cada linha tem **76 ciclos de CPU**. A linha A escreve P0 até o ciclo 6, M0
até 13, a cor de P0 até 20, PF1 até 26, PF2 até 32 e P1 até 38. PF1 começa
em X=16, no ciclo 28; P1 só usa X>=56, com seus primeiros pixels depois do
ciclo 41. A próxima linha do herói é calculada em A. Em B se prepara P1 e
se consulta `MapRows`, que fornece X/8 sem deslocamentos, para carregar a banda
do mapa. O bitmap de P0 e o Carry que habilita o laser são preparados antes
do WSYNC; Y conserva o índice usado para consultar a cor no começo de A.

Os caminhos mais longos de A cabem em 75 ciclos. Os caminhos de B, inclusive
reposicionamento, cabem em 76. Os desvios e tabelas críticos não cruzam páginas.
Alterar a ordem de instruções na janela de posicionamento pode mudar X, mesmo
que o valor de HMP1 e o total de linhas pareçam corretos.

`PositionObject` divide X por quinze: cada iteração custa cinco ciclos,
equivalentes a quinze pixels do TIA. O resto produz o ajuste fino. As escritas
indexadas têm custos diferentes das diretas de `PositionActor`; a agenda já
compensa essa diferença, o despacho e a preparação de P0 com `X_alvo-114`
para bateria/mineiro e `X_alvo-54` para o cristal. A preparação dos atores fica
no VBLANK para liberar ciclos nas janelas de reposicionamento.

TIM64T usa o primeiro decremento um ciclo após a escrita e os demais a cada
sessenta e quatro ciclos. Os valores 44 no VBLANK e 36 no overscan colocam a
expiração na última linha de cada intervalo; WSYNC alinha a região seguinte.
Não substitua esse cálculo por uma simples multiplicação por 64.

## Experimentos e verificação

Mude um comportamento de cada vez e compare a ROM anterior:

1. Troque um byte de `HeroBitmap` e observe qual linha do corpo mudou.
2. Troque `RoomRocks` para comparar a mesma geometria com outra cor NTSC.
3. Altere `WallHits` na carga da sala para testar menos impactos de laser.
4. Altere o valor inicial de `BombTimer` para comparar o tempo de fuga.
5. Mude uma banda de mapa, conferindo a mesma alteração em imagem e colisão.
   Preserve bandas 8/9 iguais enquanto usar a agenda atual de P1.

Depois de cada alteração, monte com `make build PATTERN=01-jogos/01-hero`,
execute `make check` e `make test` e recarregue a ROM no Stella. Os comandos
devem ser executados na pasta `Hero`.

Critérios de aceitação: ROM com 4096 bytes e vetores para Reset; imagem estável
de 262 linhas; teto/piso/parede bloqueando movimento; voo e queda; laser nas
duas direções; demolição e fuga da dinamite; coleta única; passagem de sala;
mineiro alcançável; resultado e reinício; oito bytes de cada ator presente em
todos os quadros, inclusive ao atravessar as janelas de reposicionamento.

`scripts/check_game.py` executa as instruções montadas e verifica esses estados,
os limites de escrita e uma partida completa por entradas de joystick. O modelo
de teste inclui CPU, RAM, timer e WSYNC, mas não pixels, prioridades, movimento
fino do TIA ou áudio. A observação no Stella descrita no README principal
complementa esses testes; ainda não houve teste em hardware real.
