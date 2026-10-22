# 01 — Mecânica básica de Space Invaders

## Objetivo

Combinar movimento, tiro e inimigos em um jogo pequeno e legível em Assembly
6507. O foco é entender como dois objetos gráficos do TIA podem representar
quatro invasores e uma nave, mantendo o fluxo de quadro explícito.

## Comportamento esperado

- A nave branca se move horizontalmente na base, limitada a X=16..144.
- Quatro invasores verdes ocupam duas colunas e duas fileiras.
- A formação se move um pixel a cada quatro quadros, inverte nas bordas e
  desce oito linhas físicas. Com dois vivos, passa a mover a cada dois quadros.
- O tiro sobe quatro linhas físicas por quadro; cada acerto remove um invasor.
- Destruir os quatro produz vitória, com fundo verde.
- A formação alcançar a faixa acima da nave produz derrota, com fundo vermelho.
- Após o fim, soltar e apertar tiro reinicia. Game Reset funciona sempre.

## Montagem e execução

Execute na raiz da pasta `SpaceInvaders`:

```sh
make build PATTERN=01-jogos/01-space-invaders
make check
make run PATTERN=01-jogos/01-space-invaders
```

No Stella, use setas esquerda/direita e Espaço, ou um joystick na porta 1.
A ROM gerada ocupa 4 KiB; NMI, RESET e IRQ apontam para `Reset`, em `$F000`.

## Objetos e coordenadas

| Recurso | Região superior | Região inferior |
| --- | --- | --- |
| Player 0, `GRP0` | Coluna esquerda dos invasores | Nave |
| Player 1, `GRP1` | Coluna direita dos invasores | Apagado |
| Missile 0, `ENAM0` | Tiro | Apagado |

O TIA possui dois players de oito pixels, não uma lista arbitrária de sprites.
Uma coluna reutiliza o mesmo player em duas alturas. Mais abaixo, o player 0 é
reposicionado para a nave. Essa reutilização **vertical**, dentro do mesmo
quadro, mantém todos os inimigos presentes a aproximadamente 60 Hz. Não há
alternância de colunas entre quadros nem dependência do filtro de fósforo.

X é medido em pixels. Y usa pares de linhas: `FleetY=12` significa início na
linha física 24 da região visível. Cada sprite tem oito bytes, repetidos em
pares, totalizando 16 linhas. A fileira inferior começa 12 pares abaixo da
superior. As colunas têm distância horizontal de 48 pixels.

Os quatro bytes de `Alive` seguem a ordem superior esquerda, superior direita,
inferior esquerda, inferior direita. `PrepareSprites` transforma esses estados
em dois buffers de 20 bytes: oito de desenho, quatro de intervalo, oito de
desenho. Um inimigo morto fornece zeros. Assim, o kernel não precisa decidir
quais inimigos estão vivos durante a geração das linhas.

## Quadro e orçamento de ciclos

| Etapa | Linhas | Trabalho |
| --- | ---: | --- |
| VSYNC | 3 | Sincronismo vertical |
| VBLANK | 37 | Entrada, movimento, colisões, buffers e posições horizontais |
| Região superior | 168 | 84 pares com invasores e tiro |
| Faixa de troca oculta | 8 | Reposicionar P0 para a nave |
| Nave | 16 | Oito pares do desenho da nave |
| Overscan | 30 | Imagem oculta antes do próximo quadro |
| **Total** | **262** | NTSC, aproximadamente 60 quadros/s |

As três partes centrais somam uma região de 192 linhas. Oito dessas linhas
ficam deliberadamente ocultas para trocar o papel do player 0.

Cada linha dispõe de 76 ciclos da CPU. No kernel superior, a linha A escreve
os objetos preparados e calcula os invasores do próximo par; a linha B mantém
os mesmos desenhos e calcula o tiro do próximo par. O pior caminho da linha A
consome 59 ciclos, contando a entrada do primeiro par; a linha B chega a 21.
Os dois players recebem seus pixels antes de suas posições horizontais.

`ALIGN` mantém os desvios do kernel na mesma página. As tabelas gráficas também
ficam dentro de uma página: cruzar uma página em certos acessos indexados
acrescentaria um ciclo. Há um salto explícito sobre o preenchimento do primeiro
`ALIGN`, para que seus bytes não sejam executados como instruções.

O timer do RIOT tem uma particularidade: o primeiro decremento depois de uma
escrita em `TIM64T` acontece após um ciclo; os seguintes usam o divisor 64.
Por isso, `44` chega a zero após `(44-1)*64+1 = 2753` ciclos e, com o alinhamento
do código, permite terminar o VBLANK em 37 linhas. Na faixa de troca, `10`
chega a zero após 577 ciclos. O `WSYNC` após cada espera fecha a linha atual.
Alterar instruções junto às escritas do timer exige revisar esses alinhamentos.

## Posição horizontal

Escrever uma coordenada em `RESP0` não posiciona diretamente um player.
O instante da escrita determina a posição aproximada. `PositionObject` usa
um laço de subtração por 15: cada volta tomada custa cinco ciclos, equivalentes
a 15 pixels horizontais. O resto vira o ajuste fino enviado a `HMP0`, `HMP1`
ou `HMM0`; `HMOVE` aplica esses ajustes no começo de uma linha.

O `STA.wx HMP0,x` força uma escrita absoluta indexada de cinco ciclos.
Encurtar a instrução muda o instante de `RESP` e desloca os objetos.
O missile recebe X+1 para compensar a diferença de reset em relação aos players.
Na faixa de troca, `HMCLR` zera os ajustes anteriores antes de reposicionar
somente P0, evitando um segundo deslocamento de P1 e do tiro.

## Colisões, estados e áudio

As colisões usam retângulos, calculados durante VBLANK. O invasor mede oito
pixels por oito pares; o tiro mede dois pixels por dois pares. O teste aceita
delta de -1 a 7 entre o início do tiro e o início do alvo. Isso inclui o caso
em que só a extremidade direita ou inferior do tiro toca o retângulo.
Pixels vazios dentro do desenho também pertencem ao retângulo de colisão.

Um acerto apaga exatamente um byte de `Alive`, reduz `Remaining` e desativa o
tiro. `State` usa 0 para jogando, 1 para vitória e 2 para derrota. Nos estados
finais, o jogo conserva as posições e aguarda novo clique. `FireReady` impede
que segurar o disparo da vitória já inicie outra partida.

O canal de áudio 0 recebe uma onda tonal no tiro e ruído no impacto.
`SoundClock` limita a duração; vitória, derrota e reinício zeram o volume.
O missile e P0 compartilham `COLUP0`: o tiro na região dos invasores é verde,
enquanto a nave na base é branca.

## Simplificações observáveis

- O tiro fica oculto ao atravessar a faixa de oito linhas acima da nave.
  Seu deslocamento e suas colisões continuam sendo calculados normalmente.
- A derrota usa o retângulo original da formação, mesmo depois de destruir
  toda a fileira inferior. O limite é `FleetY=64`, antes da faixa de troca.
- O primeiro par do tiro em Y=0 não é exibido; ele ainda aparece no par 1 e
  é removido ao sair pelo topo. Isso não interfere nos alvos, que começam abaixo.
- Não há projéteis inimigos, escudos, placar, múltiplas vidas ou novas ondas.
  Os desenhos são próprios deste estudo; a mecânica é uma redução do jogo.

## Experimentos

1. Mude os bytes de `AlienBitmap` para reconhecer a relação entre bits e pixels.
2. Altere a cor `$C8` para outra cor NTSC e observe também a cor do tiro.
3. Troque o intervalo inicial da marcha de quatro para seis quadros. A formação
   levará mais tempo para chegar às bordas, sem alterar sua velocidade vertical
   por evento de descida.
4. Mude o limiar de aceleração para um sobrevivente. Observe quando o ritmo muda.
5. Ajuste a altura do tiro de dois para um par, atualizando também a colisão.
   Compare tiros que passam rente à borda de um invasor.

Altere um comportamento por vez e remonte. Mudanças no kernel, nos espaçamentos
ou nos limites exigem revisar os ciclos, a região de troca e as 262 linhas.

## Critérios de verificação

- `make build` e `make check` devem passar, com ROM de 4096 bytes e vetores `$F000`.
- O indicador do Stella deve informar 262 linhas NTSC durante movimento e tiro.
- Todos os quatro invasores devem permanecer visíveis em cada quadro até morrerem.
- A nave deve parar nas duas margens e não deve alterar tiros já disparados.
- Cada impacto deve remover um único inimigo; o último deve produzir fundo verde.
- Sem disparar, a formação deve descer até produzir fundo vermelho.
- Segurar tiro no fim não deve reiniciar; soltar e apertar deve reiniciar.
- Game Reset deve restaurar os quatro invasores, a nave central e nenhum tiro.

O teste `scripts/check_game.py` executa a ROM no py65 e cobre controles,
32 casos de colisão, estados e timing, com um modelo mínimo do barramento.
O Stella foi usado para observar os quatro invasores, o movimento, os disparos,
as remoções e uma rodada vencida pelo teclado. Seu indicador confirmou 262 linhas
a 60 Hz. Som e hardware real não foram avaliados; a montagem e o teste da CPU
não comprovam o comportamento audiovisual completo.

## Referências técnicas

- [Stella Programmer's Guide, Atari, 1979](https://www.atariage.com/2600/programming/2600_101/docs/stella.html): TIA, objetos, sincronismo e movimento horizontal.
- [RIOT no Stella 7.0](https://github.com/stella-emu/stella/blob/7.0/src/emucore/M6532.cxx): implementação de referência consultada para a fase inicial do timer.
- [Manual do Stella](https://stella-emu.github.io/docs/index.html): controles e ferramentas do emulador.
