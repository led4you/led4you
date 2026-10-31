# LED4YOU firmware

Latest version: **v85** (see `latest.json`)

## ESP32-C3 (e.g. ESP32-C3 SuperMini, 4 MB)

| File | Use |
|---|---|
| `LED4YOU_v85_ESP32-C3_update.bin` | Update a board that already runs LED4YOU/WLED: Config → Security & Updates → Manual upload |
| `LED4YOU_v85_ESP32-C3_completo.bin` | First install over USB: flash at address **0x0** (full 4 MB image) |

On the ESP32-C3 there is one LED output (one GPIO). It uses all of the C3's LED memory, so the LEDs stay steady
while Bluetooth is on. For two or more outputs use the classic ESP32.

## ESP32 classic (e.g. ESP32 DevKit / WROOM-32, 4 MB)

| File | Use |
|---|---|
| `LED4YOU_v85_ESP32_update.bin` | Update a board that already runs LED4YOU for ESP32 |
| `LED4YOU_v85_ESP32_completo.bin` | First install over USB: erase the flash, then flash at address **0x0** (full 4 MB image) |

The ESP32 version uses a different partition layout (1.6 MB program, 700 KB files), so a board that ran
another firmware needs the full image (with erase) the first time. Never put one chip's file on the other chip.

Source code: branch [`firmware`](https://github.com/coristinaa/led4you/tree/firmware) (based on WLED 16.0.1, EUPL-1.2).
