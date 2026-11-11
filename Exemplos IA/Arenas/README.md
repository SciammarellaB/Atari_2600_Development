# Arenas — quatro chefes

Protótipo jogável para Atari 2600: quatro arenas conectadas, movimento e tiro
em oito direções, três vidas e quatro chefes com mecânicas diferentes.
Assembly 6502, **ROM de 8 KiB**, cartucho **F8**, vídeo **NTSC**. A partida
começa diretamente contra o Touro de Ferro.

## Montar e jogar

Na raiz do repositório, com DASM e Stella disponíveis:

```sh
make -C "Exemplos IA/Arenas" check
make -C "Exemplos IA/Arenas" run
```

`build` monta; `check` também confere tamanho, boot, vetores e trampoline dos
dois bancos; `run` abre o Stella explicitamente como cartucho F8 e vídeo NTSC.
A ROM fica em `build/main.bin`. `DASM`, `STELLA` e `PYTHON` permitem selecionar
os executáveis existentes. Não é necessário instalar `py65` para jogar.

## Controles

| Entrada | Ação |
| --- | --- |
| Joystick 1 / setas no Stella | Mover e apontar em oito direções |
| Botão do joystick / Ctrl esquerdo no Stella | Atirar; segurar repete |
| Soltar as direções | Parar, mantendo a orientação |
| RESET do console / F2 no Stella | Reiniciar a campanha a qualquer momento |
| Soltar e apertar o tiro na tela final | Reiniciar depois da vitória ou derrota |
| Caminhar contra uma porta aberta | Entrar na próxima arena |

Há um tiro do jogador por vez. Sua orientação fica travada ao nascer; virar o
personagem não altera um tiro em voo. As diagonais do jogador e de seu tiro
têm velocidade normalizada. O mapeamento de teclado pode ser alterado no Stella.

## Campanha e portas

```text
                       4. Senhor da Arena
                              ↑
2. Sentinela  →        3. Guardião
      ↑
1. Touro de Ferro
```

As portas ficam fechadas durante os combates. Ao derrotar um dos três
primeiros chefes, ele desaparece, os ataques são removidos e o painel mostra
**NEXT**. Abre-se uma passagem central no norte ou na parede direita, conforme
o mapa. O jogador continua se movimentando: é preciso caminhar até a abertura
para trocar de sala. Apertar tiro nessa etapa não reinicia a campanha.

A próxima arena fecha a porta e inicia o novo encontro com seis pontos de
vida para o chefe. **As vidas restantes do jogador são preservadas**; ataques,
frações de movimento e efeitos da sala anterior são descartados. Ao atravessar
para o norte, o jogador surge embaixo; ao sair pela direita, surge à esquerda.
A progressão é para a frente, sem retorno às arenas anteriores.

As aberturas comportam o corpo inteiro do jogador: no norte, X=64..88 para
seu canto esquerdo; à direita, Y=28..44 para seu canto superior. A troca exige
movimento na direção da saída, além de tocar o limite da arena.

Depois do quarto chefe, o painel mostra **WIN!** e a arena fica verde. Perder
as três vidas mostra **LOSE**, com arena vermelha. Ambos interrompem o combate
e exigem soltar e apertar o tiro novamente para reiniciar desde o primeiro
chefe. Um empate com o último chefe conta como vitória; nos demais encontros,
perder a última vida conta como derrota.

## Chefes

O jogador é a seta ciano. Os quatro chefes têm seis pontos de vida e sprites
próprios. A cor verde indica uma janela de vulnerabilidade; tiros contra a
armadura são absorvidos. O contato corporal sempre é perigoso durante o combate.

| Arena / painel | Mecânica | Janela para atacar |
| --- | --- | --- |
| Touro de Ferro / BULL | Anuncia a direção, trava a mira e investe em linha reta. Colidir com uma parede antecipa a recuperação. | Recuperação verde depois da investida |
| Sentinela / EYE! | Anuncia a mira, dispara e caminha até o próximo centro de borda: topo → direita → baixo → esquerda → topo. | Recuperação depois do disparo, inclusive enquanto caminha |
| Guardião / WARD | Fecha o escudo, anuncia o ataque e combina a investida em oito direções do Touro com um disparo. | Durante o ataque e a recuperação, ambos verdes |
| Senhor da Arena / KING | Cicla quatro padrões: faixa horizontal, corredor vertical e feixes diagonais para a direita e para a esquerda. O desenho aparece antes de causar dano. | Recuperação depois da ativação do piso |

Os avisos piscam em amarelo/laranja com pulsos sonoros. A investida do Touro e
a ativação do piso ficam vermelhas. O Guardião fica verde durante seu ataque
porque está vulnerável, mas seu corpo e seu projétil continuam perigosos.

Há no máximo uma bala inimiga por vez. A direção fica travada no disparo.
A Sentinela nasce no centro superior e, depois de cada disparo efetivo,
caminha um pixel por eixo a cada quadro até a próxima posição. Os cantos
superiores esquerdos dos quatro destinos são (72,6), (136,34), (72,62) e
(8,34); os centros do chefe ficam alinhados aos centros das quatro bordas.
Ela para exatamente no destino antes do próximo ataque. O Guardião usa os
mesmos vetores, velocidade e limites da investida do Touro, com até 64
quadros de ataque, além da bala disparada ao iniciar a investida.

As faixas retas do Senhor ficam em X=16..143, Y=34..45 (horizontal) e
X=64..95, Y=4..75 (vertical). As duas diagonais percorrem a arena de cima
para baixo, uma avançando à direita e outra à esquerda. O aviso não causa
dano; a ativação causa. Após receber um acerto, o jogador perde uma vida e pisca por cerca de
um segundo, protegido de contatos repetidos. Várias fontes simultâneas
causam no máximo um dano por quadro.

O painel inferior mostra três marcas ciano para a vida do jogador, à esquerda,
e a barra de seis unidades do chefe, à direita. O texto identifica o chefe ou
o estado da campanha.

## Implementação

- `main.asm`: banco 1, kernel, jogador, portas, sprites, painel e som;
  declara também o mapa de RAM e os pontos comuns de troca de banco.
- `bosses.asm`: banco 0, fases dos quatro chefes, mira, movimento, balas e piso.
- `combat.asm`: banco 0, colisões e resultados dos encontros.
- `beam_kernel.asm`: desenho e deslocamento dos dois feixes diagonais.
- `lab.py` e `Makefile`: montagem, verificação estrutural e execução.
- `check_arena.py`: testes da ROM montada com CPU emulada por `py65`.

O cartucho F8 contém dois bancos de 4096 bytes. Leituras em `$1FF8` / `$1FF9`
selecionam os bancos 0 / 1. Os trampolines em `$FFA0` e `$FFC0` chamam as
colisões e a lógica de chefes, retornando ao banco do kernel. Os dois bancos
têm boot idêntico em `$FFD0` e vetores
que apontam para ele, permitindo ligar o cartucho com qualquer banco inicial.

A cena tem 160 scanlines de arena e 32 de painel. A arena lógica mede 160 × 80;
o jogador ocupa 8 × 8 e o chefe 16 × 12. P0 desenha o jogador, P1 dobrado desenha
o chefe, M0 desenha o tiro de 2 × 1 e M1 desenha a bala de 4 × 2. As colisões
usam caixas nessas coordenadas. M1 é atualizado na segunda scanline do par,
com deslocamento visual de uma scanline em relação à posição lógica.
Nos dois padrões diagonais, M1 passa a desenhar um feixe de oito pixels e
anda dois pixels por faixa. As outras posições são preservadas. As colisões
consideram as duas scanlines: para o canto (X,Y) do jogador de 8 × 8, a
diagonal à direita atinge quando -7 ≤ X−2Y ≤ 23; a diagonal à esquerda,
quando 129 ≤ X+2Y ≤ 159.

Esse movimento usa HMOVE e produz o recorte preto de oito pixels na borda
esquerda da segunda scanline de cada par, somente enquanto uma diagonal
está visível. É um efeito do TIA; os demais padrões usam o kernel normal.
HMCLR aguarda pelo menos 24 ciclos após o posicionamento inicial para que
o jogador, o chefe e o tiro permaneçam nas coordenadas corretas.

O kernel escreve as paredes esquerda e direita nas duas scanlines de cada
faixa, preservando a porta lateral sem abrir a parede oposta. As faixas do
piso e a abertura superior usam tabelas de playfield selecionadas antes do
raster. Os sprites e projéteis têm janelas de leitura que evitam vazamento de
pixels. O estado usa RAM até `$DC`; a pilha dispõe de `$E0..$FF`.

Cada quadro mantém **3 linhas de VSYNC + 37 de VBLANK + 192 visíveis +
30 de overscan = 262 linhas**. O trabalho de chefes no banco 0 ocupa sempre
12 linhas, inclusive nos estados sem combate.

## Validação

Com `py65` disponível no Python selecionado:

```sh
make -C "Exemplos IA/Arenas" test
```

A suíte confere boot F8 nos dois bancos, retorno do trampoline, controles,
tiros, as quatro mecânicas, mira travada, limites, armadura/núcleo, balas,
faixas, invulnerabilidade, telas finais e reinício. Confere as quatro paradas
da Sentinela e 512 passos sem ultrapassar os destinos, a investida do Guardião
nos oito rumos e 2.246 casos de colisão, incluindo os pixels das diagonais.
Exercita também a campanha
pelas quatro salas e 756 combinações de portas fechadas, abertas e limites.

A verificação de vídeo executa 646 quadros completos, incluindo transições e
reinícios: confere 262 linhas, divisão 3/37/192/30, sprites, projéteis e prazos
dos registradores do playfield. Os testes de CPU registram escritas no TIA;
não simulam seu circuito de vídeo. A ROM F8 foi conferida visualmente no
Stella 6.7.1; a captura local está em `build/main.png`. As diagonais também
foram conferidas em cenários instrumentados no Stella, com capturas em
`build/visual_scenes/diagonal_right/main.png` e
`build/visual_scenes/diagonal_left/main.png`. Não houve teste em
console físico nem avaliação auditiva dos efeitos.

O balanceamento é inicial: esta versão prioriza os quatro padrões de combate
e a progressão pelas portas.
