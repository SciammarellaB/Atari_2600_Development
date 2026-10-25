# H.E.R.O. básico — Atari 2600

Reprodução didática em Assembly 6507, com **duas cavernas conectadas**, voo,
gravidade, laser, dinamite, parede destrutível, morcegos, baterias, cristais e
resgate de um mineiro. ROM **NTSC de 4096 bytes**, sem bankswitching.

Os desenhos foram criados para este estudo. O recorte reproduz a mecânica
central de H.E.R.O.; há uma missão com duas telas, uma tentativa por partida
e dois cristais opcionais. Não há os vinte níveis, seleção de dificuldade,
placar numérico, lava, jangadas ou vidas extras do jogo comercial.

## Montar e jogar

Execute os comandos abaixo nesta pasta. `build` monta e verifica a ROM;
`check` monta todos os padrões daqui; `run` abre o Stella.

```sh
cd /Users/sciammarella/Fontes/Estudos/Atari_2600_Development/Hero
make build PATTERN=01-jogos/01-hero
make check
make run PATTERN=01-jogos/01-hero
```

A saída fica em `build/01-jogos/01-hero/main.bin`, com listagem `main.lst` e
símbolos `main.sym`. DASM e Stella já disponíveis no computador são utilizados;
também é possível informar `DASM=/caminho/dasm` ou `STELLA=/caminho/stella`.
O lançador procura o Stella em `/Applications/Stella.app/Contents/MacOS/Stella`.
Ferramentas locais, configurações e estados desta execução ficam em `.tools/`.

**Depois de alterar ou remontar o código, recarregue a ROM no Stella.** A ROM
já aberta mantém os bytes que foram carregados anteriormente.

## Controles

| Ação | Joystick 1 | Teclado padrão do Stella |
| --- | --- | --- |
| Andar ou voar lateralmente | Esquerda/direita | Setas esquerda/direita |
| Ligar o propulsor e subir | Cima | Seta para cima |
| Cair | Soltar cima | Soltar a seta para cima |
| Atirar na direção do olhar | Botão | Espaço |
| Plantar dinamite, apoiado no chão | Baixo | Seta para baixo |
| Reiniciar a qualquer momento | Game Reset | F2 |
| Reiniciar depois do resultado | Soltar e apertar botão | Soltar e apertar Espaço |

Pode segurar o laser; apenas um disparo fica ativo de cada vez. A dinamite
exige um novo comando para cada carga: segurar baixo não planta várias.
O pavio dura aproximadamente um segundo; plante e afaste-se.

## Objetivo e painel

Na mina **ocre**, destrua a parede central e desça pelo poço inferior para
entrar na galeria **azul**. Nela, destrua a segunda parede, contorne a plataforma
central e encoste no mineiro à direita, junto ao chão. O fundo verde indica
vitória; vermelho indica derrota.

O herói tem hélice clara, capacete amarelo, uniforme azul e botas escuras,
com uma cor por faixa horizontal do desenho. Morcegos roxos causam derrota ao contato e podem
ser eliminados pelo laser. A bateria verde recupera energia; o cristal azul soma
um ao inventário. São dois tipos de coletáveis e há um de cada por caverna.

O painel espelhado mostra energia na barra superior e dinamites na inferior.
Os pequenos marcadores da faixa inferior indicam os cristais e a segunda sala.
São 64 unidades de energia, uma consumida a cada 32 quadros: aproximadamente
34 segundos sem baterias. Cada bateria recupera 24 unidades, até o máximo de 64.
A partida começa com seis dinamites, compartilhadas entre as duas salas.

## Código e explicação

- `patterns/01-jogos/01-hero/main.asm`: jogo completo, com cada bloco comentado
  em português, inclusive registradores, colisões e orçamento de ciclos.
- `include/hardware.h`: endereços e função dos registradores do TIA/RIOT.
- [README do padrão](patterns/01-jogos/01-hero/README.md): comportamento das
  rotinas, cenários, sprites, experimentos e critérios de verificação.
- `scripts/lab.py`: montagem, checagem de tamanho/vetores e abertura do Stella.
- `scripts/check_game.py`: execução da ROM no py65, incluindo percurso completo
  e regressão para impedir o retorno do flicker.

O player 0 desenha o herói, M0 desenha o laser e M1 desenha a carga de dinamite.
O player 1 é reposicionado **por altura dentro do mesmo quadro**: morcego,
bateria, cristal e mineiro aparecem em todos os quadros. Nenhum desses sprites
depende de alternância temporal ou do filtro de fósforo para ficar visível.

## Validação

Para reproduzir os testes, instale somente a dependência opcional dentro deste
exemplo. `make test` monta a ROM antes de executar os casos.

```sh
python3 -m pip install --target .tools/python py65==1.2.0
make test
```

Os testes conferem 262 linhas por quadro, 192 visíveis, prazos de escrita no
TIA, bitmaps completos em todos os quadros, colisões, energia, disparos,
explosões, coleta única, reinício e uma partida completa nas duas cavernas.
O modelo não renderiza pixels nem reproduz áudio.

A primeira caverna foi observada no **Stella 7.0**, com herói, morcego, bateria
e cristal simultâneos; seu indicador mostrou **262 linhas, 60 Hz, cartucho 4K**.
O percurso completo das duas cavernas foi validado executando a ROM no py65.
Não houve avaliação auditiva nem teste em Atari real. Há pequenos traços pretos
na margem esquerda nas linhas de HMOVE, consequência do reposicionamento do TIA.

Referências: [manual de H.E.R.O., da Activision](https://www.atariage.com/2600/manuals_old/hero.html)
e [Stella Programmer's Guide, da Atari](https://www.ataricompendium.com/archives/documents/tech_docs/2600_Stella_Guide_12-3-79_reformatted.pdf).
