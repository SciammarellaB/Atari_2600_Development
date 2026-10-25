# Menu COSMOS — Atari 2600

Exemplo independente, em Assembly 6507, contendo **apenas o menu**: título
COSMOS, melodia original em loop e seletor de **1 ou 2 jogadores**. A seta
dourada sob o número mostra a opção atual. A seleção não inicia uma partida;
o botão de tiro mantém a tela aberta.

ROM de **4096 bytes**, sem bankswitching, com vídeo **NTSC a 60 Hz**.
Todos os fontes, saídas e configurações deste exemplo ficam nesta pasta.

## Montar e executar

Com Python 3, Make, DASM e Stella instalados:

```sh
cd "/home/sciammarella/Fontes/Estudos/Atari_2600_Development/Exemplos IA/Menu"
make build
make run
```

`make build` e `make check` geram e verificam `build/main.bin`, além da
listagem `build/main.lst` e dos símbolos `build/main.sym`. `make run` monta
antes de abrir o Stella com áudio habilitado, NTSC e cartucho 4K. Se alterar
o fonte com a ROM aberta, recarregue-a no emulador.

Pode informar os executáveis com `DASM=/caminho/dasm` e
`STELLA=/caminho/stella`. O lançador também reconhece o Stella em
`/Applications/Stella.app/Contents/MacOS/Stella`. Não instala ferramentas.
O estado do emulador fica em `.tools/stella/`.

## Controles

| Ação | Atari | Teclado padrão do Stella |
| --- | --- | --- |
| Selecionar 1 jogador | Joystick 1: esquerda ou cima | Seta esquerda ou cima |
| Selecionar 2 jogadores | Joystick 1: direita ou baixo | Seta direita ou baixo |
| Alternar 1 ↔ 2 | Game Select | F1 |
| Voltar a 1 e reiniciar a música | Game Reset | F2 |

Select e Reset exigem soltar e apertar novamente. Segurar uma direção mantém
a opção. Direções contraditórias são ignoradas. Reset tem prioridade sobre
as outras entradas. Somente o primeiro controle opera o menu; escolher 2
registra a quantidade de jogadores para uma integração futura.

## Como estudar e personalizar

- `main.asm`: inicialização, leitura das entradas, música, cursor e kernel.
- `include/hardware.h`: registradores TIA/RIOT usados no exemplo.
- `scripts/graphics.py`: título, fonte, estrelas e posição dos textos.
- `scripts/lab.py`: geração dos gráficos, montagem e execução.
- `scripts/check_menu.py`: testes da ROM executando instruções no py65.

Para mudar o título, edite `text("COSMOS", 6, TITLE)` em `graphics.py`.
Inclua no dicionário `TITLE` os desenhos das letras novas e respeite o limite
de 40 colunas. `build/menu.inc` é gerado durante a montagem; não o edite.

Para alterar a música, edite `Melody` e `Envelope` em `main.asm`. A sequência
tem 32 notas, com 15 quadros cada: aproximadamente oito segundos por volta.
Usa o canal 0, tom puro, volume de 0 a 4 e uma pequena pausa entre as notas.
São alturas aproximadas do TIA, com a sonoridade característica do console.
Trocar a opção não interrompe a música.

`Players` guarda 1 ou 2 na RAM. É o ponto para um jogo futuro consultar a
seleção. Este exemplo não lê um segundo joystick nem contém jogabilidade.

## Vídeo e validação

Cada quadro tem 3 linhas de VSYNC, 37 de VBLANK, 192 visíveis e 30 de overscan.
O desenho usa 48 linhas lógicas repetidas quatro vezes. As seis tabelas de
playfield representam as metades esquerda e direita separadamente: o kernel
reescreve PF0/PF1/PF2 no meio de cada scanline para formar o texto completo.
O player 0 desenha o indicador dourado, reposicionado durante VBLANK.
Texto e cursor aparecem em todos os quadros, sem alternância temporal.

Para reproduzir os testes opcionais, instale a dependência apenas aqui:

```sh
python3 -m pip install --target .tools/python py65==1.2.0
make test
```

Os testes verificam tamanho/vetores da ROM, timing de 262 linhas, faixa
visível, repetição 48 × 4, escritas do playfield, controles, cursor, ausência
de transição pelo botão de tiro, ciclo musical e limites dos registradores
de áudio. O modelo não simula pixels nem reproduz som.

A tela foi conferida no Stella 6.7.1: título, textos e indicador para as duas
opções, com 262 linhas e 60 Hz. A melodia foi validada pelas escritas nos
registradores; não houve avaliação auditiva nem teste em Atari real.

Referências: [Stella Programmer's Guide, da Atari](https://www.atarihq.com/danb/files/stella.pdf)
e [manual do Stella](https://stella-emu.github.io/docs/index.html).
