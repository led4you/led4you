# LED4YOU — notas do projeto

Notas para retomar o trabalho numa conversa nova: o que existe, onde está, como se publica e que decisões foram
tomadas. Atualizar quando algo importante mudar.

## O que é

- **Firmware**: WLED 16.0.1 com usermods LED4YOU, para **ESP32‑C3** (SuperMini, 4 MB) e **ESP32** clássico (4 MB).
- **App**: página web instalável (PWA), por Bluetooth ou Wi‑Fi: <https://led4you.github.io/led4you/>
- **LED4YOU Studio**: zonas, texto, imagens, "Os meus LEDs", épocas… (na app e embutido na placa).
- **Cubo das crianças** (`show/`): os visitantes leem um QR e mandam mensagem, imagem, efeito ou desenho para um cubo
  de matrizes, através de ntfy.sh e de uma ponte (`ponte_show.py`) que corre no Raspberry Pi do FPP.
- **Pacote de GIFs**: 77 GIFs 16×16 desenhados por código.

## Onde está

| O quê | Onde |
|---|---|
| Site, app, GIFs, cubo, binários | repo `led4you/led4you`, branch **main** (GitHub Pages) |
| Código do firmware | mesmo repo, branch **firmware** (WLED + `usermods/led4you_ble/`) |
| Usermods LED4YOU | `usermods/led4you_ble/` (`led4you_ble.cpp`, `l4y_extras.cpp`, `studio/`, `app/`, `gifpack/`, `patches/`) |
| Versão do firmware | `L4Y_FW_VERSION` em `usermods/led4you_ble/l4y_extras.cpp` |
| Bibliotecas alteradas | `usermods/led4you_ble/patches/` (NeoPixelBus `NeoEsp32RmtMethod.h`, AnimatedGIF) |
| Configuração de compilação | `usermods/led4you_ble/platformio_override.led4you.ini` (ambientes `led4you_c3` e `led4you_esp32`) |
| Gerador dos GIFs | `usermods/led4you_ble/gifpack/make_gifs.py` (saída em `gifs/` + `pack.json` do site) |
| Traduções | `i18n.js` (app; cópia em `i18n/i18n.js` para as páginas da placa) e `i18n/wled_t.js` (páginas do WLED) |

O endereço antigo `coristinaa.github.io/led4you` deixou de funcionar quando a conta mudou de nome (novembro de 2026):
a app tem de ser instalada outra vez a partir do endereço novo, e as placas abaixo da v91 têm de ser atualizadas à mão.

## Como se publica

**Firmware vN**
1. Subir `L4Y_FW_VERSION`; compilar `led4you_c3` e `led4you_esp32`.
2. Verificar o tamanho: C3 ≤ 1 572 864 bytes, ESP32 ≤ 1 703 936 bytes (a v96 ficou grande demais e foi recusada).
3. Em `firmware/` (branch main): `vN/{esp32c3,esp32}` com bootloader + partições, `boot_app0.bin`,
   `LED4YOU_vN_<chip>_update.bin`, e o `…_completo.bin` feito com `esptool merge_bin`
   (C3: 80m, bootloader em 0x0; ESP32: 40m, bootloader em 0x1000; dio, 4 MB).
4. `manifest-vN.json`, `latest.json`, `versions.json` (as 3 últimas); apagar a versão mais antiga e os `completo`
   da anterior; atualizar o README de `firmware/`.
5. O Studio embutido: correr `studio/build_studio.js` e embutir antes de compilar quando `studio.js`/`i18n.js` mudam.

**App vNN**: subir `i18n.js?v=`, `studio.js?v=`, "LED4YOU app vNN" em `index.html` e `CACHE` em `sw.js`;
copiar para `usermods/led4you_ble/app/` (e `studio/`) no branch firmware.

**Cubo**: alterar `show/ponte_show.py`, regenerar `show/instalar_ponte.sh` (leva a ponte lá dentro), atualizar
`show/LEIA-ME.md`. No Pi: FPP › Content Setup › File Manager › Scripts › Upload `instalar_ponte.sh` › Run.
A página dos visitantes (`show/index.html`) só precisa de push.

## Regras do dono do projeto

- **Pedir antes** de mexer no Raspberry Pi ou numa placa; nunca gravar ou enviar nada para a placa sem confirmação.
- Ficheiros novos com versão no nome (v2, v3…), para comparar com os antigos.
- **Ambiente de trabalho** (`C:\Users\Gregorio\Desktop`): só as últimas versões, já descomprimidas
  (`LED4YOU_App_vNN`, `LED4YOU_vN_*.bin`, `LED4YOU_Show_vN`); apagar as anteriores.
- **Sem Alexa e sem MQTT nas placas.** Não enviar nada para o repositório oficial do WLED.
- PixelForge fica como está por agora.
- Respostas em português de Portugal.

## Decisões técnicas importantes

- **ESP32‑C3, saídas de LEDs**: 1–2 saídas → a 1.ª por SPI + DMA, a 2.ª por RMT com os 2 blocos de memória;
  3–4 saídas → todas por SPI em modo quad (uma linha de dados cada), sem RMT. Dividir o RMT entre 2 saídas encravava
  os LEDs com Bluetooth. O Modo de teste da app já não é preciso na C3 (v96+).
- **ESP32 clássico**: a 1.ª saída por I2S; as saídas 2–4 por RMT com 2 blocos de memória cada (v101).
- **Memória**: a C3 com Bluetooth fica justa. Abaixo de ~12 KB livres a placa recusa memória nova; abaixo de 10 KB
  durante 15 s pára os GIFs. O decodificador de GIF partilha a memória de trabalho, e cada GIF a mais gasta ~1–2 KB
  (até 4 GIFs ao mesmo tempo nas duas placas, enquanto houver memória).
- **Espaço do programa na C3**: sobram ~19 KB; ESP‑NOW e Adalight estão desligados na C3.
- **Zonas**: guardadas em `/l4yzones.json` e repostas no arranque, também com preset de arranque (v98) e depois de
  uma atualização (v100). Mudar as saídas de LEDs volta as zonas ao início, de propósito.
- **Painéis**: não pode haver coluna ou linha vazia **entre** painéis (estragava imagens e texto); a app impede.
- Problemas de "saídas que não funcionam" foram várias vezes **cabos com mau contacto**: confirmar os fios primeiro.

## Cubo das crianças

- Página de controlo (só na rede de casa): <http://192.168.1.97:8099>
- Visitantes, Halloween: <https://led4you.github.io/led4you/show/?t=l4yshow-3352b4beefd1&tema=hw>
- Visitantes, Natal: <https://led4you.github.io/led4you/show/?t=l4yshow-3352b4beefd1&tema=xm>
- Ponte v16 (imagens e desenhos animados pelos visitantes; v15: volta a um preset depois de X min sem pedidos): cada lado é independente, um pedido novo substitui logo o anterior (opção para esperar a vez), sem
  espera entre pedidos (configurável), tempos até 5 min (efeito 3 min de origem), opção "deixar o último pedido",
  efeitos sugeridos + todos os da placa, com cores e paleta.
- Cartazes A3 (Natal, Halloween) e seta de direção: canvas "Cartaz A3 – Cubo das crianças" no Claude.

## Ideias em aberto

- Pré-visualizações reais dos efeitos: gravar os efeitos a partir do cubo (a pré-visualização atual é uma imitação).
- Sistema de fotos no cubo (câmara no Pi, fotos guardadas só no Pi; atenção ao RGPD com crianças).
- Cubo noutra rede: aparelho com a ponte nessa rede (recomendado) ou MQTT só no ESP32 clássico.
- Pausar o cubo enquanto o FPP toca o show (MQTT do FPP, só na ponte).

- App v98: novo cartão "Texto com animação" no separador Texto (Bluetooth): em cima / ao meio / em baixo / duas linhas, cor e direção por linha, movimento, efeito de fundo, cor de fundo, velocidade. Gera GIF no telemóvel e envia como l4y-texto-a/b.gif (alterna).
- App v99: Criar um GIF ganhou "As imagens mexem: ao mesmo tempo / à vez" (como no cubo), com 2+ imagens e Saltar/Pulsar/Tremer.
- Firmware v104 (só código, ainda não compilado — esta sessão não chega aos servidores do PlatformIO): Studio por Wi-Fi com "Texto com animação" e "Criar um GIF"; studio.js minificado no build_studio.js (precisa de npm ci), página fica 101 166 bytes gz (antes 101 788), por isso cabe na C3.
- App v100 / cubo: cada linha de texto pode "Ficar parada" (além de esquerda/direita).
- App v101 / cubo: direção de cada linha = parado / esquerda / direita / cima / baixo (a direção já faz mexer, sem escolher "Atravessar"); texto de lado (letras em coluna) no cartão de texto e no cubo. Linha maior que a matriz não fica parada: passa para a esquerda (ou para cima, de lado).
- App v102 / cubo: tamanho do texto (Automático = o maior que cabe conforme o movimento; Pequeno/Médio/Grande/Muito grande); "Atravessar" em 4 sentidos (esquerda, direita, cima, baixo) para imagens e texto. No cubo, o fx vai para a ponte como "slide" (a ponte v16 não precisa de mudar).
- Firmware v104 publicado (2026-11-20): Studio por Wi-Fi com Texto com animação e Criar um GIF (app v102). C3 1 555 904 bytes, ESP32 1 618 160. Compilado offline: plataforma/framework/toolchains do GitHub (crosstool-NG esp-2021r2-patch5 .tar.gz), tool-scons feito com pip, libs clonadas em /tmp/libs com os patches, dependências dos library.json tiradas só durante a compilação.
- App v103 / cubo: "Fica parado" é sempre parado. Linha um pouco comprida demais: letras juntas (sem espaço), uma sim uma não mais escura; se nem assim couber fica cortada e aparece um aviso.
