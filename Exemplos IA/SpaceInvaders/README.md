# Space Invaders básico — Atari 2600

Exemplo de estudo em Assembly 6507: nave, tiro, quatro invasores em formação
2 × 2, marcha lateral, descida nas bordas, colisões, vitória e derrota.
Os quatro invasores são desenhados em **todos os quadros**, sem alternância
temporal de colunas. Os exemplos anteriores do repositório permanecem separados.

## Executar

Neste diretório, com DASM e Stella já instalados:

```sh
make build PATTERN=01-jogos/01-space-invaders
make check
make run PATTERN=01-jogos/01-space-invaders
```

`build` monta a ROM e verifica seus vetores. `check` monta/verifica os padrões
disponíveis nesta pasta. `run` monta/verifica antes de abrir o Stella em NTSC.
Se necessário, passe `DASM=/caminho/dasm` ou `STELLA=/caminho/stella` ao `make`.
O lançador reconhece também `/Applications/Stella.app/Contents/MacOS/Stella`.
Nenhuma ferramenta é instalada globalmente pelo exemplo.

A ROM fica em `build/01-jogos/01-space-invaders/main.bin`, acompanhada de
`main.lst` e `main.sym`. Trata-se de uma ROM de **4096 bytes**, sem bankswitching.

## Controles

| Ação | Joystick 1 | Teclado padrão do Stella |
| --- | --- | --- |
| Mover a nave | Esquerda/direita | Setas esquerda/direita |
| Atirar | Botão | Espaço |
| Reiniciar após vitória/derrota | Soltar e apertar o botão | Soltar e apertar Espaço |
| Reiniciar a qualquer momento | Chave Game Reset | F2 |

É permitido segurar o tiro: um novo disparo acontece depois que o anterior
acerta um inimigo ou sai pelo topo. Há somente um tiro ativo.

## Como estudar

O código principal está em `patterns/01-jogos/01-space-invaders/main.asm`.
Os comentários explicam cada bloco, registradores, valores e restrições de timing.
O [README do padrão](patterns/01-jogos/01-space-invaders/README.md) detalha
o kernel, os estados, os experimentos e os critérios de verificação.

Este recorte não inclui tiros inimigos, escudos, placar, vidas ou novas ondas.
A vitória deixa o fundo verde; a derrota deixa o fundo vermelho. A formação
acelera quando restam dois invasores e perde ao atingir a faixa acima da nave.

## Validação

Além de `make check`, há testes opcionais que executam a ROM montada no py65:

```sh
python3 -m pip install --target .tools/python py65==1.2.0
PYTHONPATH=.tools/python python3 scripts/check_game.py
```

Essa dependência fica somente em `.tools/`. Os testes verificam timing com um
modelo mínimo de WSYNC/timer, controles, colisões, vitória, derrota e reinício.
Não simulam a imagem, o ajuste horizontal do TIA nem o som.

Na validação deste exemplo, a ROM foi montada com DASM 2.20.17 e observada no
Stella 7.0: quatro invasores simultâneos, nave, disparos, remoção de inimigos e
vitória obtida jogando pelo teclado. O indicador do Stella mostrou **262 linhas,
60 Hz e cartucho 4K**. Não houve teste em um Atari real nem avaliação auditiva.
