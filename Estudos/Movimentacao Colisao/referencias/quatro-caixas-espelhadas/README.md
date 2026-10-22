# Referência: quatro caixas espelhadas

## Objetivo e comportamento

Preservar a versão anterior para comparar o playfield espelhado simples com
o cenário assimétrico atual. Jogador branco de 8 × 16, quatro caixas amarelas
de 16 × 32, fundo azul, movimento contínuo e colisão AABB por eixo.

O jogador inicia em (40,80). As caixas ocupam [32,48) × [40,72),
[112,128) × [40,72), [56,72) × [112,144) e [88,104) × [112,144).
São dois pares refletidos em X = 80. Encostar é permitido; entrar é impedido.

## Explicação

CTRLPF = 1 espelha a metade esquerda. PF1 = $0F nas faixas de 8 linhas
5..8 desenha o primeiro par; PF2 = $3C nas faixas 14..17 desenha o segundo.
As tabelas têm 24 entradas, sem trocas de playfield no meio da linha.

AABB usa quatro retângulos e quatro esperas WSYNC por eixo. Desfazemos apenas
a coordenada bloqueada para permitir deslizar nas diagonais. O quadro tem
3 linhas de sincronismo, 37 de preparação, 192 visíveis e 30 de overscan.
O código contém comentários explicando os blocos de hardware, fluxo e timing.

## Montagem da referência

Na pasta principal deste estudo, crie build/ pela montagem normal. Em seguida,
o DASM monta este fonte em arquivos distintos, preservando a ROM atual:

```sh
make build
dasm referencias/quatro-caixas-espelhadas/main.asm -f3 -obuild/quatro-caixas-espelhadas.bin -lbuild/quatro-caixas-espelhadas.lst -sbuild/quatro-caixas-espelhadas.sym
```

Para observar esta ROM, abra build/quatro-caixas-espelhadas.bin no Stella,
selecionando NTSC e cartucho 4K. A montagem deve produzir 4096 bytes com
NMI/RESET/IRQ em $F000. A observação audiovisual é uma etapa separada.

## Experimentos e verificação

Compare as posições simétricas, os blocos sólidos e as faixas de 8 linhas com
a versão atual. Teste as quatro caixas, diagonais e limites da tela; confira
262 linhas por quadro. Esta cópia foi remontada e teve tamanho/vetores
conferidos na preservação; os testes audiovisuais desta versão foram realizados
na etapa anterior do estudo. Não houve verificação em hardware real.
