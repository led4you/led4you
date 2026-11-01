# LED4YOU

**LED4YOU** são luzes de Halloween e Natal com LEDs WS2812B, controladas a partir do telemóvel por **Bluetooth** ou **Wi‑Fi**.
O firmware é uma versão própria do [WLED](https://github.com/wled/WLED) 16.0.1, com uma app e funções feitas para decorações de época.

👉 **App:** https://led4you.github.io/led4you/ (abre no Chrome ou no Edge e pode ser instalada como app)

---

## O que faz

- **App por Bluetooth**: liga-te às luzes sem Wi‑Fi, escolhe efeitos, cores, paletas e presets, e configura o Wi‑Fi e os LEDs.
- **Página da placa por Wi‑Fi**: todas as funções do WLED, mais o **LED4YOU Studio**.
- **Pré-visualização**: animações de cada efeito, paleta, tema e cena antes de os escolheres, e a imagem ao vivo das tuas luzes.
- **Texto em matriz**: movimento para a esquerda, direita, cima e baixo, 5 tipos de letra, degradê e arco-íris, **emojis** e acentos (á, ã, ç…).
- **Os meus LEDs**: cada LED com a sua cor e comportamento (fixo, piscar, respirar, cintilar, arco-íris), com modo de desenho.
- **Imagens e GIFs**: pacote de GIFs de Halloween, Natal e festas, e os teus próprios GIFs.
- **Épocas**: temas prontos de Halloween e Natal e efeitos próprios (Candy Cane, Snowfall, Haunted, Retro Tree).
- **Ver na casa**: experimenta os efeitos numa árvore, casa, jardim ou janela antes de pores as luzes.
- **Leitura com a câmara**: a app encontra onde está cada LED (como na Twinkly) e mostra os efeitos numa foto das tuas luzes.
- **Cenas da casa**: um toque muda todas as placas LED4YOU da casa ao mesmo tempo.
- **Horário**: ligar e desligar a uma hora ou ao pôr e nascer do sol, temporizador, contagem decrescente e loop de presets.
- **Som e movimento**: efeitos com microfone e sensor de movimento (PIR) para sustos de Halloween.
- **xLights**: as placas podem receber espetáculos do xLights por Wi‑Fi.
- **4 línguas**: português, inglês, espanhol e francês.
- **Atualização com um toque** a partir da página da placa.

## Placas suportadas

| Placa | Ficheiros em [`firmware/`](firmware/) |
|---|---|
| **ESP32‑C3** (por exemplo ESP32‑C3 SuperMini, 4 MB) | `LED4YOU_vXX_ESP32-C3_…` |
| **ESP32** clássico (por exemplo ESP32 DevKit / WROOM‑32, 4 MB) | `LED4YOU_vXX_ESP32_…` |

Nunca uses o ficheiro de um chip no outro.

## Instalar numa placa nova

**Mais fácil:** abre a [app](https://led4you.github.io/led4you/) no **Chrome ou Edge de um computador**, liga a placa por USB e usa o cartão
**Instalar o LED4YOU numa placa nova**: escolhes a versão e o ficheiro certo para o chip (ESP32‑C3 ou ESP32) é gravado sozinho.

**À mão:**

1. Abre o [ESP Tool da Espressif](https://espressif.github.io/esptool-js/) no Chrome ou no Edge do computador.
2. Liga a placa por USB e carrega em **Connect** (se não ligar, segura o botão **BOOT** ao ligar o cabo).
3. Carrega em **Erase Flash**.
4. Em **Flash Address** escreve `0x0`, escolhe o ficheiro **`…_completo.bin`** do teu chip e carrega em **Program**.
5. Abre a [app](https://led4you.github.io/led4you/), liga-te por Bluetooth à placa **LED4YOU‑xxxx** e configura o Wi‑Fi e o pino dos LEDs.

## Atualizar

- **Mais fácil:** na página da placa aparece um aviso quando há uma versão nova; um toque e a placa atualiza-se sozinha com o ficheiro certo para o seu chip.
- **À mão:** na página da placa, **Config › Security & Updates › Manual upload**, com o ficheiro **`…_update.bin`** do teu chip.

A versão mais recente está sempre em [`firmware/latest.json`](firmware/latest.json).

## Estrutura deste repositório

| Pasta / ficheiro | O que é |
|---|---|
| `index.html`, `studio.js`, `layouts.js`, `scanner.js`, `sw.js` | A app (página web instalável) |
| `i18n/` | Traduções da app e das páginas da placa |
| `gifs/` | Pacote de GIFs originais |
| `fonts/` | Letras com emojis e acentos para o texto |
| `firmware/` | Ficheiros para gravar e atualizar as placas |
| branch [`firmware`](https://github.com/led4you/led4you/tree/firmware) | Código-fonte do firmware (WLED 16.0.1 + usermods LED4YOU) |

---

## English

LED4YOU is a WLED 16.0.1 based firmware and web app for Halloween and Christmas LED decorations (WS2812B), controlled over
Bluetooth or Wi‑Fi. It runs on ESP32‑C3 and classic ESP32 boards (4 MB). Open the app at https://led4you.github.io/led4you/,
flash a new board with the `…_completo.bin` file at address `0x0`, and update later from the board's own page.

## Licença

Baseado no [WLED](https://github.com/wled/WLED), licenciado sob a **EUPL‑1.2**. O código do firmware LED4YOU está no branch `firmware` sob a mesma licença.
Os GIFs e as letras com emojis são originais deste projeto.
