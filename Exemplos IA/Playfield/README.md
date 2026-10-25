# Mansão de nove salas — Atari 2600

Protótipo em Assembly 6507 de exploração **vista de cima**, inspirado na
estrutura de uma mansão de survival horror: fundo preto, paredes e móveis
claros, portas fechadas, objetos coletáveis e dois puzzles. O personagem
começa no **Vestíbulo (sala 1), desarmado, com 00 balas e 3 pontos de vida**.
Não há inimigos nem dano nesta etapa.

A ROM usa **F4 de 32 KB**, com oito bancos de 4 KB, e vídeo **NTSC**. O cenário
tem rolagem vertical dentro de cada sala e um painel inferior fixo.

## Executar

Requer Python 3, Make, DASM e Stella instalados:

```sh
cd "/home/sciammarella/Fontes/Estudos/Atari_2600_Development/Exemplos IA/Playfield"
make build
make run
```

`make build` gera `build/main.bin` com 32.768 bytes. `make check` também monta
e verifica a ROM. `make run` abre o Stella com cartucho F4, formato NTSC e
áudio habilitado. Para ver alterações em uma ROM já aberta, recarregue-a.
Os caminhos dos executáveis podem ser definidos com `DASM` e `STELLA`;
as configurações locais do emulador ficam em `.tools/stella/`.

O build monta cada banco separadamente em `build/bank0/` até
`build/bank7/`, com `main.bin`, `main.lst`, `main.sym` e `rooms.inc` próprios.
Também gera `build/rooms-bank0.inc` até `rooms-bank7.inc`, a fonte comum
`build/hud.inc` e cópias da listagem e dos símbolos do banco 0 em
`build/main.lst` e `build/main.sym`. Os arquivos gerados não devem ser
editados manualmente.

## Controles e navegação

| Ação | Atari / teclado padrão do Stella |
| --- | --- |
| Andar | Joystick 1 / setas |
| Atirar, após encontrar arma e balas | Botão do joystick 1 / espaço |
| Recolher objeto ou ativar switch | Passar sobre ele |
| Abrir porta azul com a chave | Aproximar-se da porta |
| Reiniciar jogo, recursos, puzzles e música | Game Reset / F2 |
| Visitar a próxima sala, para depuração | Game Select / F1 |

O personagem anda em **oito direções**. Combine duas setas para andar na
diagonal; direções opostas no mesmo eixo são ignoradas. É possível andar
e atirar ao mesmo tempo. O segundo controle não tem função. Reset tem
prioridade sobre Select, e ambos exigem soltar antes de uma nova ativação.

A troca de sala acontece ao **atravessar uma abertura**. O corpo inteiro
precisa caber no vão; paredes, móveis e portas fechadas bloqueiam o
movimento. Ao atravessar, o jogador entra pelo lado oposto e preserva a
coordenada transversal. As aberturas laterais ocupam as linhas lógicas
20–27; as superiores e inferiores ficam nas colunas 18–21.

O mapa abaixo mostra todas as conexões. Linhas comuns são passagens livres;
as ligações marcadas dependem dos puzzles. Não há ligação vertical entre
Enfermaria e Biblioteca nem entre Biblioteca e Quarto: isso impede
contornar as portas fechadas.

```text
[6 Galeria: balas] ----- [7 Escritório] ---- AZUL ---- [8 Quarto: vida]
        |                     |
[3 Jantar: arma] ------- [4 Hall] ------- VERMELHA -- [5 Biblioteca: chave]
        |                     |
[0 Cozinha: switch] ---- [1 Vestíbulo: início] ------- [2 Enfermaria: balas]
```

`F1` visita as nove salas em sequência, com uma posição inicial segura,
preservando recursos e puzzles. Esse é um atalho de depuração que ignora
a progressão da exploração; para jogar o percurso, use as passagens.
`F2` volta ao Vestíbulo, restaura a vida, remove arma e munição, devolve os
objetos às salas e fecha as duas portas.

## Coletas e puzzles

Há no máximo um objeto em cada sala. Todos ficam em **x=32..39 pixels TIA,
y=34..37 linhas lógicas**, na parte inferior esquerda do mapa. A coleta
acontece quando o centro do jogador (`PlayerX+4`, `PlayerY+2`) entra nessa
área, sem botão de interação. Os objetos não bloqueiam o movimento nem os
tiros. Uma coleta permanece registrada ao sair da sala e voltar.

| Sala | Objeto | Efeito |
| --- | --- | --- |
| 0 — Cozinha | Switch vermelho | Abre permanentemente a passagem 4 ↔ 5 |
| 1 — Vestíbulo | Nenhum | Sala inicial |
| 2 — Enfermaria | Balas | Soma 12, limitado a 99 |
| 3 — Jantar | Arma | Habilita o tiro quando houver munição |
| 4 — Hall | Nenhum | Dá acesso à porta vermelha |
| 5 — Biblioteca | Chave azul | Fica no inventário até abrir a porta azul |
| 6 — Galeria | Balas | Soma 12, limitado a 99 |
| 7 — Escritório | Nenhum | Dá acesso à porta azul |
| 8 — Quarto | Vida | Restaura a vida para 3 |

O switch da Cozinha abre a porta vermelha entre Hall e Biblioteca. Ele
continua vermelho, mas passa de preenchido para um desenho vazado
(`ObjectMask=$81`), indicando que já foi ativado. Pisar novamente não fecha
a porta e não repete a ação.

A chave da Biblioteca abre a porta azul entre Escritório e Quarto quando
o jogador se aproxima do vão. A abertura **consome a chave**, e a porta
continua aberta até Reset. O acesso é reconhecido dos dois lados. A arma
é permanente até Reset; munição e vida desaparecem ao serem recolhidas.
O item de vida é consumido mesmo com a vida cheia. Como ainda não há dano,
a exploração mantém os três pontos iniciais.

Um percurso possível é explorar a Cozinha, encontrar a arma no Jantar e
as balas na Galeria ou Enfermaria, entrar na Biblioteca pela porta vermelha
e levar a chave até a porta azul do Escritório. Não há tela de vitória ou
condição de derrota nesta etapa.

## Painel e câmera

A área visível tem **160 scanlines de cenário + 32 de painel**. O painel
mostra coração e até três segmentos de vida, quantidade de balas em dois
dígitos e ícones da arma e da chave carregadas. Ele usa somente o playfield;
seus glifos são montados depois do cenário, reutilizando os buffers em RAM.
`scripts/hud.py` gera os números 3×5, coração, barras e ícones.

Cada sala tem **40 colunas × 48 linhas lógicas**. Uma célula equivale a
quatro pixels horizontais do TIA por quatro scanlines. A janela mostra 40
linhas; `CameraY` varia de 0 a 8, permitindo acessar as oito linhas que
ficam fora dela. A câmera acompanha quando o jogador passa das linhas 8
ou 28 dentro da janela e para nas bordas da sala. A rolagem avança em
passos de quatro scanlines.

Jogador, objetos, portas, tiros e colisões continuam em coordenadas da
sala inteira. O desenho usa `RowStart+CameraY`; a altura do personagem é
`PlayerY-CameraY`. `ShotViewY` recorta o projétil na janela, inclusive quando
só aparecem três scanlines no topo ou uma no rodapé. Sair da janela não
troca de sala: a passagem depende dos limites e aberturas do mapa. Todos
os objetos são desligados antes de desenhar o painel.

## Recursos gráficos e animação

| Recurso do TIA | Função |
| --- | --- |
| Playfield | Paredes, móveis, aberturas e painel |
| P1 | Personagem azul/ciano, 8 pixels × 16 scanlines |
| P0 | Objeto da sala, 8 pixels × 16 scanlines |
| M0 | Porta vermelha ou azul, 4 pixels × 32 scanlines |
| M1 | Projétil azul/ciano, 2 pixels × 4 scanlines |
| Bola | Disponível |

O personagem tem **oito linhas de oito bits**, cada byte repetido por
**duas scanlines**. O desenho é uma matriz 8×8 exibida em 8 pixels TIA × 16
scanlines; oito linhas de desenho não significam oito scanlines físicas.
Os pixels horizontais e as scanlines têm proporções diferentes no sinal
de TV, portanto essas medidas não correspondem a uma grade de pixels
quadrados modernos.

Há cinco poses para cada uma das quatro direções: parado, passo A, passo B,
disparo e recuo. São 20 poses e 160 bytes em `PlayerGraphics`, escritos em
binário. Cada `1` acende um pixel e cada `0` deixa aparecer o cenário. Por
exemplo, a pose parada olhando para baixo é:

```asm
DownIdle
        byte %00111100
        byte %01111110
        byte %01011010
        byte %00111100
        byte %01111110
        byte %10111101
        byte %00100100
        byte %01100110
```

Os objetos P0 usam **quatro bytes de oito bits**, repetidos por quatro
scanlines cada. Assim também ocupam 8×16, com definição vertical menor que
a do jogador. `ObjectRows` contém os glifos; `ObjectMask=0` esconde um item
recolhido, `$FF` o mostra inteiro e `$81` modifica o switch ativado.

P0 e M0 compartilham `COLUP0`. Para usar uma cor nos objetos e outra nas
portas, `GateRows` contém **cores por linha**, atualizadas antes dos pixels
dos objetos.
O bit 0, ignorado pela cor NTSC, indica a faixa da porta: `$47` (vermelho)
ou `$87` (azul). Deslocar esse bit e aplicar `GateMask` fornece o valor 2
para `ENAM0` quando a porta está fechada. Fora da faixa, a cor-base `$46`
ou `$86` é preservada, sem habilitar o míssil. As linhas dos objetos usam
outras cores com bit 0 desligado. Porta e objeto
ocupam alturas diferentes, permitindo compartilhar o registrador sem
recolorir as paredes. P1 e M1 compartilham a cor azul/ciano de `COLUP1`.

## Movimento, colisão e tiro

`PlayerX` varia de 0 a 152 pixels TIA e `PlayerY` de 0 a 44 linhas lógicas.
A cada dois quadros, o jogador tenta andar dois pixels horizontais e/ou
uma linha lógica vertical. A diagonal move os dois eixos no mesmo passo,
sem normalização de velocidade. Se a posição candidata colidir, ambos
param; não há deslizamento automático pela parede.

`CanStand` consulta todas as células ocupadas pelo corpo 8×16, usando as
mesmas tabelas PF do desenho e `CollisionPages/CollisionMasks`. São quatro
linhas e duas ou três colunas, conforme o alinhamento. Testar apenas os
cantos permitiria atravessar uma parede fina no meio do corpo. As portas
fechadas acrescentam a barreira da passagem. A interação com objetos usa
o centro do jogador e não os registradores de colisão do TIA.

A caminhada alterna os passos a cada quatro movimentos bem-sucedidos.
Parar ou encontrar uma parede retorna à pose parada. Nas diagonais, a
orientação horizontal tem prioridade para a pose, mas o movimento e a
mira preservam a diagonal. `Aim` guarda a última direção válida; ao atirar,
ela é copiada para `ShotDir`, sem curvar uma bala já lançada.

O tiro exige o bit de arma em `Weapon` e pelo menos uma bala em `Ammo`.
Há **um projétil por vez**. Segurar Fire repete o disparo quando o projétil
anterior termina e o recuo acaba. Cada novo ataque consome uma bala,
inclusive contra uma parede. `Ammo` usa BCD de `00` a `99`; o código entra
em modo decimal para soma e subtração e o desliga em seguida.

O projétil anda a cada quadro: dois pixels horizontais e/ou uma linha
lógica vertical. Paredes, portas fechadas e limites da sala o removem. Ele
não coleta itens, aciona switches nem atravessa para outra sala. Trocar de
sala também remove a bala. `AttackTimer` mantém seis quadros de disparo e
seis de recuo, usando o mesmo P1 e a mesma colisão do personagem.

## Música e efeitos

A trilha **Tensão** toca automaticamente em dois canais durante a
exploração: 64 passos, 15 quadros por passo e aproximadamente 16 segundos
por volta em NTSC a 60 Hz. O canal 0 toca a melodia cromática em onda
quadrada; o canal 1 intercala baixo pulsante e percussão de ruído. A música
usa metade do volume dos envelopes, arredondando para baixo. A cópia fica
neste projeto e compila sem depender do exemplo `Musica`.

Cada tiro inicia seis quadros de ruído descendente. Coletas, ativação do
switch e abertura da porta azul chamam `PlayActionSound`, com dois tons
ascendentes durante 12 quadros. Os efeitos usam temporariamente o canal 1;
a melodia e o sequenciador continuam. A ação tem prioridade sobre o tiro,
e uma nova ação reinicia o próprio efeito. Não há fila. Ao terminar, o
canal 1 retorna à posição atual da música. Passagens e Select preservam a
trilha; Reset reinicia música e efeitos junto com o jogo.

## ROM, RAM e temporização

F4 seleciona um dos oito bancos de 4 KB por acessos a `$FFF4..$FFFB`.
`LoadRoom` lê `RoomBanks` e troca de banco antes de consultar os dados da
sala. Código, rotinas comuns e vetores ocupam os mesmos endereços em todos
os bancos, de modo que a próxima instrução continua válida após a troca.
Cada banco comporta até duas salas: bancos 0–3 têm duas, banco 4 tem a sala
8 e um slot vazio, e bancos 5–7 não têm salas. Mesmo esses bancos incluem
Reset, que seleciona o banco da sala inicial.

A ROM maior permite os nove mapas, mas replica o código comum em cada
banco e exige um cartucho compatível com F4. Ela não aumenta a RAM nem o
tempo disponível por scanline. O build verifica o tamanho de cada banco,
os vetores e a igualdade dos endereços dos símbolos. Guardas de montagem
impedem que blocos invadam páginas ou alcancem a área dos hotspots.

`rooms.py` converte `#` e `.` em seis tabelas PF alinhadas em páginas de
256 bytes. Cada tabela tem 96 bytes para os dois slots de sala; as caudas
das páginas recebem rotinas e dados de áudio, HUD e mundo. `ObjectRows`
tem o mesmo tamanho; `GateRows` acrescenta uma sentinela zero. `EXITS`
continua separado do desenho. Os três registradores `PF0/PF1/PF2` são
reescritos no meio da linha para desenhar metades independentes, com
`CTRLPF=0`; o cenário não é espelhado.

| Endereços RAM | Uso |
| --- | --- |
| `$80..$99` | Estado de sala, jogador, tiro, câmera e recursos |
| `$9A..$C1` | Buffer das primeiras duas scanlines de P1 por linha lógica |
| `$C2` | `ObjectGraphic`, reutiliza a sentinela superior |
| `$C3..$EA` | Buffer das últimas duas scanlines de P1 por linha lógica |
| `$EB` | `NextColor`, reutiliza a sentinela inferior |
| `$EC..$EE` | Passo e relógio da música, estado do efeito |
| `$EF..$F2` | Puzzles, dois bytes de coletas e máscara do objeto |
| `$F3..$FF` | 13 bytes reservados à pilha |

Entrada e colisão reutilizam `$9A..$A4` fora do desenho. No overscan,
`UpdateShot` e `UpdateWorld` rodam antes de `ClearSpriteRows`, que limpa os
82 bytes dos buffers; a música é atualizada em seguida. No VBLANK,
`BuildSpriteRows` limpa os temporários e prepara a pose relativa à câmera.
Após o cenário, `BuildHud` reutiliza esses buffers para glifos e ponteiros
do painel. Novas variáveis ou chamadas aninhadas precisam respeitar a
separação entre buffers, estado persistente e pilha.

O quadro é composto por **3 scanlines de VSYNC + 37 de VBLANK + 160 de
cenário + 32 de painel + 30 de overscan = 262 scanlines**. Os temporizadores
usam `TIM64T=43` no preparo do cenário, `9` no preparo do painel e `35` no
overscan. O painel tem oito linhas de preparo, cinco linhas de glifos
repetidas quatro vezes e quatro linhas de rodapé. A sequência de escritas
no TIA é sensível a ciclos; mudar o kernel exige conferir novamente a
posição dos objetos, o playfield e o número de linhas do quadro.

## Arquivos e verificação

| Arquivo | Responsabilidade |
| --- | --- |
| `main.asm` | Kernel, jogador, tiro, colisão, transições e música |
| `include/world.h` | Coletas, persistência e puzzles |
| `include/hud_kernel.h` | Câmera, preparação e desenho do painel |
| `include/sound_effects.h` | Efeitos e prioridade entre tiro e ação |
| `include/hardware.h` | Registradores TIA/RIOT |
| `scripts/rooms.py` | Nove mapas, conexões, objetos e dados de cada banco |
| `scripts/hud.py` | Fonte e ícones codificados para o playfield |
| `scripts/lab.py` | Montagem F4, validação estrutural e lançamento do Stella |
| `scripts/check_playfield.py` | Verificações executando instruções da ROM no py65 |

Os testes usam uma dependência instalada apenas nesta pasta:

```sh
python3 -m pip install --target .tools/python py65==1.2.0
make test
```

O modelo py65 permite verificar lógica, RAM, bancos e ciclos das instruções,
mas não reproduz integralmente os pixels e o comportamento do TIA/RIOT.
A verificação no Stella complementa os testes com navegação, coletas,
cores, recorte dos objetos e estabilidade do painel. Não houve teste em
Atari físico.

`make test` passou com um percurso de 1.024 passos pelas nove salas,
coletas e puzzles, 54 quadros de renderização e dois loops completos da
música. As regressões conferem as janelas de escrita do PF, inclusive a
primeira scanline das paredes. Capturas nativas em
`build/screenshots/mansion/` confirmaram as portas completas nos dois lados,
suas aberturas, coleta da chave e da arma e consumo de munição. A visão
das nove salas está em `build/screenshots/mansion/planta-mansao.png`.

Edite cenários, conexões e glifos dos objetos em `scripts/rooms.py`, poses
em `PlayerGraphics`, regras de coleta em `include/world.h` e ícones do
painel em `scripts/hud.py`. Mantenha passagens recíprocas, rotas acessíveis
ao corpo inteiro e espaço livre nas posições dos objetos.

Referências: [manual original da Atari](https://www.atariage.com/2600/programming/2600_101/docs/stella.html)
e [manual do Stella](https://stella-emu.github.io/docs/index.html).
