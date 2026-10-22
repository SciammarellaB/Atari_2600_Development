# Cenário assimétrico, caixas detalhadas e colisão AABB

## Objetivo

Desenhar quatro caixas fixas sem espelhamento, com contornos e travessas internas.
O cenário usa células de **4 pixels × 2 linhas**, em vez de 4 × 8. As duas
metades têm dados independentes; as caixas ocupam posições sem simetria.

O jogador continua branco, com 8 × 16 pixels, movimento de 1 pixel horizontal
ou 2 linhas verticais por quadro e os mesmos limites externos. As caixas medem
16 × 32 e permanecem sólidas: os vazios azuis internos são textura, não passagens.
ROM de 4 KiB, NTSC, sem bankswitching ou dependências adicionais.

A versão anterior está preservada em
[referencias/quatro-caixas-espelhadas/](referencias/quatro-caixas-espelhadas/README.md).
Ela permite comparar o kernel espelhado simples com o kernel assimétrico atual.

## Comportamento esperado

O jogador inicia em `(40, 80)`, fora das caixas, e é controlado pelo joystick 1
(normalmente as setas no Stella). Encostar é permitido; entrar é impedido.
Na diagonal, o eixo livre permite deslizar pelas paredes. Nenhuma caixa se move.

As posições abaixo usam direita/base exclusivas:

| Caixa | Esquerda | Direita | Topo | Base |
| --- | --- | --- | --- | --- |
| Superior esquerda | 24 | 40 | 32 | 64 |
| Superior direita | 92 | 108 | 48 | 80 |
| Inferior esquerda | 48 | 64 | 120 | 152 |
| Inferior direita | 124 | 140 | 104 | 136 |

A caixa 1, por exemplo, ocupa X = 24..39 e Y = 32..63. Não existe uma fórmula
que reflita suas coordenadas para definir outra caixa. Todas são independentes.

## Renderização: duas metades por linha

`CTRLPF = 0` desliga a reflexão, mas o TIA normalmente repetiria os mesmos
20 bits do playfield na metade direita. Para realmente separar os desenhos,
o kernel precisa substituir PF0/PF1/PF2 durante a própria linha.

Há seis tabelas de 96 bytes: `SceneLeftPF0/1/2` e `SceneRightPF0/1/2`.
Cada índice Y representa duas linhas visíveis. Primeiro o kernel fornece os
bits da esquerda; depois que cada registrador terminou seu trecho esquerdo,
fornece os bits da direita, antes de eles serem usados novamente.

Em cada metade, a ordem horizontal é PF0 bits 4..7, PF1 bits 7..0 e PF2 bits
0..7. Um bit representa 4 pixels. As tabelas guardam contornos e travessas em
faixas de duas linhas, oferecendo quatro vezes mais definição vertical que
as tabelas anteriores, sem mudar a largura física da célula do playfield.

Cada tabela começa em uma página de 256 bytes. Assim `LDA tabela,Y`, com
Y = 0..95, custa sempre 4 ciclos. Aumentar a tabela além da página pode mudar
os ciclos e quebrar a imagem: esses alinhamentos fazem parte do kernel.

## Kernel de duas linhas e jogador

`DrawFirstLine` e `DrawSecondLine` desenham a mesma faixa. A duplicação das
instruções é deliberada: cada linha tem só 76 ciclos; chamadas de subrotina
ou cálculos adicionais no meio da linha consumiriam o orçamento disponível.

`PlayerPixels` guarda o padrão do jogador da faixa atual. No fim da primeira
linha, calculamos `NextPlayerPixels`; a segunda ainda usa o padrão atual.
Somente ao terminar a segunda linha promovemos o próximo padrão e incrementamos Y.

Durante a preparação do quadro, `PlayerRowBefore = YPos / 2 - 1`. A expressão
`(Y - PlayerRowBefore) < 8` prepara os pixels do jogador para a faixa seguinte.
Isso depende de YPos par, mantido pelo início em 80 e pelos passos verticais de 2.
Oito faixas correspondem às 16 linhas do jogador. A faixa inicial 0 começa
vazia porque o limite superior do jogador é Y = 16.

As escritas abaixo são medidas em ciclos de CPU após cada WSYNC:

| Escrita | Primeira linha | Segunda linha |
| --- | --- | --- |
| GRP0 | 9 | 6 |
| PF0 esquerdo | 16 | 13 |
| PF1 esquerdo | 23 | 20 |
| PF2 esquerdo | 30 | 27 |
| PF0 direito | 39 | 36 |
| PF1 direito | 46 | 43 |
| PF2 direito | 53 | 50 |

A primeira linha tem um prefixo de 3 ciclos: `STA VBLANK` na entrada inicial,
`JMP DrawFirstLine` nas demais. Os dois caminhos deixam as mesmas posições
para as escritas. O `NOP` entre as metades garante a espera necessária.

PF0 esquerdo termina no ciclo 28; PF1 em 38⅔; PF2 em 49⅓. As substituições
direitas ocorrem depois desses limites e antes de o TIA precisar dos novos
bits. Remover um NOP ou mudar uma instrução pode alterar a metade errada.

O quadro continua com `3 + 37 + 192 + 30 = 262` linhas. A preparação reserva
13 WSYNC em `ReadJoystick`, 2 em `PositionPlayer`, 21 na espera e o primeiro
WSYNC do kernel. O cálculo de `PlayerRowBefore` cabe antes do posicionamento.
O último WSYNC visível deixa a linha 191 terminar antes do overscan de 30 linhas.

## Colisão separada da textura

A colisão continua usando quatro AABBs e é executada antes da imagem visível.
O jogador precisa sobrepor uma caixa nos dois eixos ao mesmo tempo:

```text
X < caixa.direita  e  X + 8 > caixa.esquerda
Y < caixa.base     e  Y + 16 > caixa.topo
```

`BlockRights`, `BlockMinX`, `BlockBottoms` e `BlockMinY` vêm das constantes
geométricas. Os mínimos reorganizam as somas: X + 8 > esquerda equivale a
X >= esquerda - 8 + 1; Y usa altura 16. Os limites deste estudo cabem em 8 bits.

`CheckCollision` percorre as quatro caixas, uma por WSYNC, sempre com a mesma
quantidade de linhas. `CollisionFound` acumula o resultado e `LSR` o devolve
no carry. A rotina altera A/X/flags e preserva Y; não lê colisão do TIA.

`ReadJoystick` tenta X, testa e restaura se bloqueado; depois faz o mesmo para
Y usando o X aceito. Essa prioridade horizontal permite deslizar na diagonal.
A posição final de cada tentativa é testada: velocidades muito maiores
exigiriam verificar também o trajeto para evitar saltar um obstáculo.

Os retângulos representam o corpo inteiro da caixa, inclusive seus detalhes
azuis internos. Desenho e geometria continuam separados: alterar uma constante
de posição exige atualizar as entradas correspondentes nas tabelas gráficas.

## Montar e executar

Na raiz do repositório, os comandos selecionam este estudo e geram os artefatos
em seu `build/`: `main.bin`, `main.lst` e `main.sym`.

```sh
make -C "Estudos/Movimentacao Colisao" build
make -C "Estudos/Movimentacao Colisao" check
make -C "Estudos/Movimentacao Colisao" run
```

As variáveis `DASM` e `STELLA` permitem indicar executáveis existentes.
`check` monta e verifica somente tamanho e vetores. Testes de CPU, timing e
observação no Stella são verificações separadas, descritas abaixo.

## Experimentos e critérios de verificação

1. Compare com a referência espelhada: as caixas atuais devem ter posições
   diferentes em X e Y, sem cópias refletidas ou repetidas aparecendo.
2. Aproxime-se de todas as caixas e tente entrar nelas. A textura não deve
   permitir atravessar; o contato não deve mover as caixas.
3. Contorne cantos, use diagonais e teste os limites externos da tela.
4. Para mudar apenas a textura, preserve o contorno e altere os bits internos
   nas tabelas. A AABB pode continuar igual.
5. Para deslocar uma caixa, ajuste suas constantes e os bits das tabelas da
   metade correspondente. A resolução é de 4 pixels em X e 2 linhas em Y.
6. Preserve o alinhamento das tabelas e reconfira os ciclos ao alterar o kernel.
   Verifique 262 linhas por quadro e procure pixels duplicados na outra metade.

## Validação desta implementação

- DASM 2.20.16: build/check aprovados; ROM de 4096 bytes e vetores `$F000`.
- Decodificação independente dos 30.720 pixels: quatro texturas nas posições
  corretas e metades independentes; contornos externos coincidem com as AABBs.
- ROM executada com py65 existente: 65.536 pares X/Y de colisão aprovados;
  126.160 casos de movimento com 16 combinações de direções, sem atravessar caixas.
- Revisão independente: 694 quadros estáveis com 262 linhas; máximo de 74 ciclos
  antes de WSYNC. Foram conferidas 42.048 linhas visíveis e todas as escritas
  nos ciclos da tabela. O jogador tem 16 linhas corretamente alinhadas em todos
  os 73 valores pares de Y; os 137 valores horizontais também foram conferidos.
- Stella 7.0: cenário detalhado assimétrico e contato com cada uma das quatro
  caixas observados. Indicador manteve 262 linhas a aproximadamente 60 Hz.
  Diagonais foram testadas na CPU simulada, sem teste manual simultâneo.
- Não houve teste em hardware real. Os testes de CPU/pixels foram feitos
  à parte e não são executados automaticamente por `make check`.
