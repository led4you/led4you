# Cubo das crianças (LED4YOU) — v13

As crianças leem o código QR na parede e, no telemóvel, escrevem uma mensagem (ou escolhem uma pronta do tema),
escolhem uma imagem animada ou fazem um desenho.
O pedido aparece logo no lado escolhido e substitui o que lá estava. Cada lado é independente: enquanto um lado
mostra um texto, os outros recebem outros pedidos. Com a opção "Cada pedido espera que o anterior acabe", os
pedidos para o mesmo lado esperam pela vez, por ordem de chegada.

O cubo é **à parte do show**: não entra nas sequências do xLights nem no FPP. A ponte fala diretamente com a placa
LED4YOU / WLED do cubo.

```
telemóvel ──► página pública ──► ntfy.sh (canal do cubo) ──► ponte_show.py (em casa) ──► placa do cubo
```

A rede de casa nunca fica aberta para a internet: é a ponte, em casa, que vai buscar os pedidos.

## 1. Instalar a ponte (uma vez)

**Mais fácil, num Pi com o Falcon Player (FPP), sem comandos:** na página do FPP vá a **Content Setup › File Manager**,
separador **Scripts**, carregue em **Upload** e escolha `instalar_ponte.sh`. Depois, na linha do ficheiro, carregue em
**Run**. O script põe a ponte em `/home/fpp/`, faz com que arranque sozinha com o Pi e mostra o endereço da página de
controlo. Para atualizar a ponte, faça o mesmo com o `instalar_ponte.sh` novo.

**À mão:**

Corre em qualquer computador da rede de casa com Python 3. Pode ser o Raspberry Pi do FPP: é um programa
separado, na porta 8099, e não mexe no FPP. Não precisa de instalar mais nada.

1. Copie `ponte_show.py` para o Pi (por exemplo para `/home/fpp/`).
2. Arranque: `python3 ponte_show.py`
3. No telemóvel ou no computador, **na rede de casa**, abra a página de controlo: **http://IP-DO-PI:8099**

Para arrancar sozinha com o Pi, crie `/etc/systemd/system/ponte-show.service`:

```
[Unit]
Description=LED4YOU cubo das criancas
After=network-online.target

[Service]
ExecStart=/usr/bin/python3 /home/fpp/ponte_show.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

e depois `sudo systemctl enable --now ponte-show`.

## 2. Preparar a placa do cubo

Na app LED4YOU, crie **uma zona por lado** do cubo (por exemplo Frente, Trás, Esquerda, Direita, Topo).
Cada zona é uma matriz com o seu tamanho.

## 3. Página de controlo (http://IP-DO-PI:8099)

- **Mostrar os pedidos dos visitantes**: liga e desliga a qualquer altura. Desligada, a página diz que as luzes
  não estão a receber pedidos e não deixa enviar.
- **Procurar placas na rede** → escolha a placa do cubo.
- **Lados do cubo**: marque as zonas que são lados e dê-lhes um nome. As crianças escolhem o lado pelo nome.
  "Todos os lados" só aparece quando os lados têm todos o mesmo tamanho.
- **Tema**: só conta para quem abre a página sem tema no endereço. Os QR do Halloween e do Natal já trazem o tema.
- **Tempo** de cada mensagem, imagem, efeito (3 minutos de origem) e desenho.
- **Espera entre pedidos do mesmo telemóvel**: 0 de origem (sem espera).
- **Deixar o último pedido nas luzes até chegar outro**: dá tempo para tirar fotografias.
- **Deixar escrever texto livre**: ligado de origem. Se o desligar, só se podem enviar as mensagens prontas.
- **Aprovar cada pedido**: os pedidos ficam em "Por aprovar", com os botões Mostrar / Recusar.
- **Códigos QR**: dois, um para cada tema, com o botão Copiar endereço. **Não mudam**: pode mudar lados ou tempos
  sem reimprimir.
- **Testar** e **Registo**.

Carregue em **Guardar** depois de mudar. As escolhas ficam em `show_config.json`.

## Halloween e Natal: um QR para cada

| Tema | Endereço | Página |
|---|---|---|
| Halloween | `https://led4you.github.io/led4you/show/?t=l4yshow-3352b4beefd1&tema=hw` | roxo e laranja, mensagens e imagens de Halloween |
| Natal | `https://led4you.github.io/led4you/show/?t=l4yshow-3352b4beefd1&tema=xm` | verde e vermelho, mensagens e imagens de Natal |

Ponha no cartaz de Halloween o QR do Halloween e no cartaz de Natal o QR do Natal.

## Como funciona

- **Mensagem**: escrita pela criança (até 40 letras, sem acentos nas luzes) ou uma das prontas do tema.
- **Imagem**: GIF do LED4YOU GIF pack. A ponte confirma que o GIF está na placa e, se não estiver (por exemplo depois
  de "Apagar todos os GIF" na app), vai buscá-lo ao site e envia-o outra vez.
- **Imagem em todos os lados**: o ESP32 (firmware v90 ou mais nova) mostra até 4 GIF ao mesmo tempo, um por lado;
  a C3 (firmware v99 ou mais nova) também até 4, mas só enquanto houver memória (com Bluetooth ligado, 2 ou 3).
- **Efeito** (v8): 6 efeitos por tema (Halloween: casa assombrada, olhos, fogo, relâmpagos…; Natal: neve, bengala
  doce, árvore, estrelas, fogo de artifício…). O número de cada efeito é pedido à própria placa.
  Por baixo, **todos os efeitos da placa** (v12), com caixa de procura; ficam de fora os de som e os que piscam
  muito. Desliga-se na página de controlo em "Mostrar aos visitantes todos os efeitos da placa".
  Com **pré-visualização** do efeito no tamanho do lado escolhido, **duas cores** e a **paleta de cores** (v13).
- **Desenho**: 9 cores, com o tamanho do lado escolhido.
- Quando um lado acaba e não tem mais pedidos, volta ao que mostrava antes.

## Cuidados

- **Palavrões**: o texto livre passa por um filtro (português e inglês, também com números). Nenhum filtro é
  perfeito: se aparecer algo que não quer, ligue a aprovação ou desligue o texto livre.
- **Espera em cada telemóvel** conforme a página de controlo (0 de origem) e, na ponte, **no máximo 20 pedidos por
  minuto** no total (o mesmo pedido repetido em 3 s é ignorado); no máximo 20 pedidos em fila ou por aprovar.
- O canal do ntfy.sh é público: quem souber o código pode enviar pedidos. A ponte só aceita pedidos válidos
  (mensagens prontas, imagens do pack, desenhos do tamanho certo). Para mudar o código, mude `topic` em
  `show_config.json` e reimprima o QR.
- A página de controlo não tem palavra-passe: só é acessível na rede de casa, e só aceita ordens dela própria
  (um site qualquer aberto num telemóvel da rede de casa não consegue mudar as definições).
