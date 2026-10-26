# Mansão — 15 salas em três andares / Atari 2600

Protótipo de exploração vista de cima, em Assembly 6507: subsolo com quatro
salas, térreo com cinco salas em L e andar superior com seis salas. O jogador
começa no **Saguão (T1), desarmado, com 0 balas e 3 corações**. A partida
termina ao conseguir a chave dourada e atravessar a saída do Saguão.

Esta etapa implementa a planta, escadas, exploração, coletas, switches,
chaves coloridas, portas e encerramento. Inimigos, dano e notas com texto
ficam para as próximas etapas. É possível usar a arma e gastar munição,
mas ainda não há alvos.

## Executar

Requer Python 3, Make, DASM e Stella:

```sh
cd "/home/sciammarella/Fontes/Estudos/Atari_2600_Development/Exemplos IA/Playfield"
make build
make run
```

A ROM `build/main.bin` tem **32.768 bytes**, cartucho **F4**, vídeo **NTSC**.
`make check` também monta e verifica o cartucho. `make run` abre o Stella
com áudio; uma ROM que já estava aberta precisa ser recarregada. Os
executáveis podem ser definidos por `DASM` e `STELLA`; as configurações do
emulador ficam em `.tools/stella/`.

## Controles

| Ação | Atari / Stella |
| --- | --- |
| Andar em oito direções | Joystick 1 / setas |
| Atirar, com arma e munição | Fire / espaço |
| Recolher item ou ativar switch | Passar sobre ele |
| Abrir porta com a chave correspondente | Aproximar-se da porta |
| Subir ou descer uma escada | Atravessar a abertura com degraus |
| Reiniciar tudo | Game Reset / F2 |
| Visitar a próxima sala, para depuração | Game Select / F1 |

Reset tem prioridade sobre Select. Ambos precisam ser soltos antes de uma
nova ativação. Select percorre as 15 salas, preservando recursos e puzzles;
é um atalho de depuração que ignora a progressão. Depois da fuga, movimento,
Fire e Select ficam inativos; Reset inicia outra partida.

## Planta e progressão

Os códigos identificam salas lógicas, não bancos do cartucho.

```text
SUBSOLO
[B1 Depósito] ----- [B2 Serviço / escada para T3]
      |
[B3 Despensa] -- VERDE -- [B4 Gerador]

TÉRREO EM L
                                      [T5 Escadaria para A4]
                                               |
                                        [T4 Biblioteca]
                                           VERMELHA
                                               |
SAÍDA -- DOURADA -- [T1 Saguão] -- [T2 Galeria] -- [T3 Hall / escada para B2]

ANDAR SUPERIOR
[A1 Quarto] -- [A2 Enfermaria] -- AZUL -- [A3 Escritório]
     |
[A4 Patamar / escada para T5] -- [A5 Retratos] -- ROXA -- [A6 Suíte]
```

B2 é a sala superior direita do conjunto de quatro do subsolo. As duas
ligações entre andares são **B2 ↔ T3** e **T5 ↔ A4**. Os degraus pertencem
ao playfield decorativo e são atravessáveis. A subida usa a abertura
superior; a descida, a inferior. Não é necessário apertar Fire.

O Gerador só tem entrada pela Despensa; o Escritório só pela Enfermaria;
a Suíte só pela sala de Retratos. Isso impede contornar as portas fechadas.

Um percurso completo:

1. Do Saguão, chegar ao Hall e descer para B2. Explorar o Depósito para
   encontrar a arma e a Despensa para ativar o switch vermelho.
2. Voltar ao Hall: a passagem para a Biblioteca está aberta. Subir pela
   Escadaria e encontrar a chave verde na Enfermaria.
3. Retornar ao subsolo. A chave verde abre o Gerador, onde está a chave azul.
4. Voltar à Enfermaria e usar a chave azul para entrar no Escritório.
   O switch roxo abre a Suíte.
5. Buscar a chave dourada na Suíte e voltar ao Saguão. Abrir a porta
   dourada e atravessar para fora conclui a partida.

A arma e as balas não são requisitos dos puzzles. Não há condição que
obrigue gastar munição para conseguir a saída.

| Índice | Sala | Objeto |
| --- | --- | --- |
| 0 | B1 — Depósito | Arma |
| 1 | B2 — Sala de serviço | Nenhum |
| 2 | B3 — Despensa | Switch vermelho |
| 3 | B4 — Gerador | Chave azul |
| 4 | T1 — Saguão | Nenhum; saída final |
| 5 | T2 — Galeria | Nenhum |
| 6 | T3 — Hall | Nenhum |
| 7 | T4 — Biblioteca | Balas |
| 8 | T5 — Escadaria | Vida |
| 9 | A1 — Quarto | Balas |
| 10 | A2 — Enfermaria | Chave verde |
| 11 | A3 — Escritório | Switch roxo |
| 12 | A4 — Patamar | Nenhum |
| 13 | A5 — Sala de retratos | Nenhum |
| 14 | A6 — Suíte | Chave dourada |

Os itens ficam em x32..39 pixels TIA, y34..37 linhas lógicas, em recantos
acessíveis. O centro do corpo (`PlayerX+4`, `PlayerY+2`) ativa a coleta.
Cada objeto só pode ser recolhido uma vez por partida. Balas somam 12,
limitadas a 99; vida restaura três corações, mesmo se já estiver cheia.

Chaves verde, azul e dourada são consumidas ao abrir suas portas. As portas
permanecem abertas; os switches também são permanentes e ficam vazados
após o uso. A arma permanece no inventário. Ao escapar, a cena fica dourada
e o painel mostra corações dourados e uma coroa. Não há texto no final.

## Cenário, câmera e movimento

Cada sala tem **40 × 48 células**, com quatro pixels TIA horizontais e
quatro scanlines por célula. A janela exibe 40 linhas lógicas: **160
scanlines de cenário**, mais **32 scanlines de painel fixo**. `CameraY`
varia de 0 a 8, acompanha o jogador e para nas bordas. A troca de sala ocorre
nas aberturas do mapa, não ao sair da janela da câmera.

O corpo usa oito pixels TIA por 16 scanlines; `PlayerX` varia de 0 a 152,
`PlayerY` de 0 a 44. Um passo desloca dois pixels horizontais e/ou uma linha
lógica vertical. Um acumulador soma 77 por quadro nas retas ou 54 nas
diagonais e tenta o passo quando passa de 255: aproximadamente 18 e 12,7
passos por segundo. Isso deixa a caminhada reta cerca de 40% mais lenta
que a versão original, com a diagonal compensada em aproximadamente 1/√2.

A fase persiste ao parar, trocar direção, colidir ou atravessar salas.
Entradas neutras ou opostas não avançam o acumulador; tocar repetidamente
o controle não acelera o jogador. Uma colisão interrompe os dois eixos,
sem deslizamento automático. A orientação horizontal prevalece na diagonal,
mas a mira preserva os dois componentes. A animação alterna a cada quatro
movimentos bem-sucedidos.

`scripts/mansion.py` define mobiliário, pisos e paletas. Tapetes, juntas e
degraus são decorativos. A colisão usa os volumes inteiros de paredes e
móveis, independentemente dos pixels vazados do desenho. O cenário usa
playfield assimétrico (`CTRLPF=0`), com uma cor de primeiro plano por sala
e tons de fundo por linha lógica. A cor de fundo muda no HBLANK da segunda
scanline; a primeira ainda mantém o tom anterior.

Os interiores incluem caixas e máquinas no subsolo; colunas, bancos e
biblioteca no térreo; quartos, biombos, escritório e suíte no superior.
T2 e A5 reutilizam o mesmo desenho, piso e colisão de galeria, com cor de
primeiro plano e estado de porta próprios. São **15 salas lógicas e 14
templates gráficos**, mantendo o cartucho de 32 KB.

## Sprites, portas e tiros

| Recurso do TIA | Cenário |
| --- | --- |
| Playfield | Paredes, móveis, chão e degraus |
| P1 | Personagem |
| P0 | Item ou switch da sala |
| M0 | Porta fechada |
| M1 | Projétil |
| Bola | Disponível |

O personagem tem 20 poses, cinco para cada direção: parado, dois passos,
disparo e recuo. Cada pose usa oito bytes binários, repetidos por duas
scanlines, formando 8×16. Os objetos P0 usam quatro bytes de oito bits,
repetidos por quatro scanlines. A proporção de pixels TIA e linhas de TV
não equivale a pixels quadrados modernos.

Portas laterais usam M0 com oito pixels × 32 scanlines em x0 ou x152.
Portas superiores/inferiores usam oito pixels × quatro scanlines em x76,
no centro da abertura; o corpo não cabe nos quatro pixels restantes de
cada lado. A colisão acompanha exatamente esses retângulos. Porta e objeto
compartilham `COLUP0`, com cores por linha em `GateRows`; o bit0 indica
quando habilitar M0 e não altera a cor NTSC.

A bala exige arma e munição. Há um projétil por vez; manter Fire repete o
disparo depois do recuo. Cada tiro consome uma bala. `Ammo` usa BCD00..99;
modo decimal é desligado após a soma/subtração. O projétil anda dois pixels
horizontais e/ou uma linha lógica vertical por quadro e é removido por
paredes, móveis, portas, limites ou mudança de sala. Não coleta itens nem
atravessa para outra sala. `ShotBlocked` verifica as duas linhas lógicas
tocadas pelo míssil numa única caixa, percorrendo a mobília uma vez.

## Painel com chaves coloridas

Três corações ficam à esquerda; bala × quantidade, no centro; arma e
chaves, à direita. A quantidade omite o zero inicial. Corações e números
continuam com nove linhas de desenho, cada uma repetida duas vezes.

O inventário tem **18 scanlines independentes**: arma nas seis primeiras,
chave verde nas quatro seguintes, depois azul e dourada, quatro linhas
cada. Todas podem aparecer simultaneamente, sem alternância de quadros.
Na vitória, a coroa substitui o inventário.

P0 tem três cópias em x12/28/44; P1 mostra bala em x72, números em x88/x104
e inventário em x136. `NUSIZ1` muda de3 para6 no ciclo61. `COLUP1` volta
para branco no ciclo8 e recebe a cor do inventário no ciclo64; `GRP1` muda
nos ciclos21/50/56/67. Assim, as cores das chaves não atingem os números.
`GRP0` muda nos ciclos14/30/36. Cada linha usa 75 ciclos incluindo a espera
seguinte; não há HMOVE ou reposicionamento durante os glifos.

## Música e efeitos

A trilha Tensão toca em dois canais: 64 passos, 15 quadros por passo, cerca
de 16 segundos por volta a 60Hz. O volume usa metade dos envelopes. Tiros
usam seis quadros de ruído; coletas, switches, portas e fuga usam dois tons
durante 12 quadros. A ação tem prioridade sobre o tiro; ambos usam o canal1
sem reiniciar o sequenciador. Salas e Select preservam a trilha; Reset
reinicia música e efeitos. Os dados estão nesta ROM, sem dependência do
projeto irmão de música.

## Bancos, RAM e temporização

F4 seleciona oito bancos por `$FFF4..$FFFB`. Os bancos0..6 compartilham
código e metadados, com dois templates por banco. `RoomStarts`, `RoomEnds`
e `RoomSolidStarts/RoomSolidEnds` selecionam os dados do template. O banco7
é exclusivo do painel.

`RoomBanks` ocupa `$FFD0..$FFDE` nos oito bancos e mapeia as 15 salas
lógicas. Tanto `LoadRoom` quanto o retorno do painel usam essa tabela;
o banco não é mais calculado por `Room >> 1`. Os trampolins em `$FFE0`
e `$FFE6` preservam a execução ao trocar bancos. Reset começa com cinco
bytes iguais, selecionando o banco0 antes de inicializar a partida.

As seis tabelas PF, `ObjectRows` e `GateRows` são alinhadas em páginas,
com 96 bytes por par de templates; `GateRows` inclui uma sentinela extra.
`FloorColors` tem96bytes e `SolidRects` reserva160bytes. O primeiro retângulo
de cada template é a porta dinâmica; `CollisionBox` o ignora quando aberto.
As galerias compartilhadas usam o mesmo retângulo físico, mas `GateMask`
permite que só A5 tenha a porta da Suíte. Caudas das páginas recebem rotinas
e metadados. O build protege tamanhos, alinhamentos, vetores e trampolins.

| RAM | Uso |
| --- | --- |
| `$80..$99` | Sala, jogador, movimento, tiro, câmera, vida, munição e inventário |
| `$9A..$C1` | Primeiras duas scanlines de P1 por linha lógica |
| `$C2` | `ObjectGraphic`, sentinela superior |
| `$C3..$EA` | Últimas duas scanlines de P1 por linha lógica |
| `$EB` | `NextColor`, sentinela inferior |
| `$EC..$EE` | Música e efeito sonoro |
| `$EF` | Puzzles e vitória |
| `$F0..$F1` | Quinze bits de coletas |
| `$F2` | Máscara do objeto |
| `$F3..$FF` | Pilha |

O painel reutiliza os buffers: cinco glifos variáveis de nove bytes,
inventário em `$D0..$E1`, temporário `$E2` e cores `$E3..$E6`. A bala estática
é lida da ROM. Não altera os estados persistentes a partir de `$EC`.

O quadro usa **3 VSYNC + 37 VBLANK + 160 cenário + 32 painel + 30 overscan
= 262 scanlines**. `TIM64T` usa43 no preparo do cenário,13 no painel e35 no
overscan. O painel reserva12linhas de preparo,18de glifos e2de rodapé.
A velocidade da caminhada não altera a frequência do vídeo, dos tiros ou
da música.

## Fontes e validação

| Arquivo | Responsabilidade |
| --- | --- |
| `scripts/world.py` | Planta, IDs, conexões, escadas, itens, chaves e portas |
| `scripts/mansion.py` | Arte, paletas e volumes estáticos |
| `scripts/rooms.py` | Empacotamento de templates e metadados |
| `main.asm` | Kernel, personagem, movimento, tiro, navegação e trilha |
| `include/world.h` | Coletas, abertura de portas e puzzles |
| `include/collision.h` | Colisão de caixas com volumes e portas |
| `include/hud_kernel.h` | Câmera e entrada no painel |
| `hud.asm` | Kernel do painel no banco7 |
| `scripts/hud.py` | Glifos, inventários coloridos e coroa |
| `include/hud_bank_switch.h` | Trocas entre cenário e painel |
| `include/sound_effects.h` | Efeitos e prioridade do áudio |
| `scripts/lab.py` | Montagem e verificações estruturais da ROM |
| `scripts/check_playfield.py` | Regressões executando a ROM no py65 |

```sh
python3 -m pip install --target .tools/python py65==1.2.0
make test
```

Os arquivos de `build/` são gerados, incluindo `bank0/` até `bank7/`,
`bank-map.inc`, `hud.inc`, `hud_link.inc`, listagens e símbolos. Não devem
ser editados manualmente. `.tools/` guarda dependências e configurações
locais; não integra o cartucho.

O py65 confere instruções, RAM, bancos, lógica e ciclos, mas não reproduz
integralmente o TIA/RIOT. As capturas nativas do Stella complementam a
validação de pixels, cores, portas e estabilidade. Não houve teste em
Atari físico. As capturas desta versão ficam em
`build/screenshots/mansion15/`.

Validação desta versão: `make test` passou com um percurso físico de
2.816 passos até a fuga; o grafo de 230 estados de progressão não contém
becos sem saída. Foram conferidas 29.900 posições livres sem ilhas, 5.430
caixas de colisão, 7.916 diagonais, 28 passagens incluindo quatro travessias
de escadas, 9.600 colisões de tiros e 6.464 combinações do painel. Os 90
quadros de salas/câmeras, 512 quadros de movimento e dois loops completos
da trilha preservaram 262 scanlines. Os maiores custos medidos foram
1.813 ciclos no preparo do cenário e 1.632 no overscan, dentro dos budgets.

No Stella, 45 estados foram capturados e as três imagens finais de cada
estado foram idênticas: todas as salas nas câmeras0/8, inventário nas três
cores, vitória e portas abertas/fechadas, inclusive verticais. As posições
das portas coincidiram com seus retângulos físicos. Foram comparadas
189.168 amostras do playfield e 61.440 pixels do painel com os desenhos,
cores e posições esperados, sem diferenças.

`mansao-15-salas.png` reúne os ambientes completos combinando duas posições
de rolagem; o jogo exibe uma janela por vez. `inventario-chaves.png` mostra
arma, chaves, posse simultânea e vitória.

Referências: [manual original da Atari](https://www.atariage.com/2600/programming/2600_101/docs/stella.html)
e [manual do Stella](https://stella-emu.github.io/docs/index.html).
