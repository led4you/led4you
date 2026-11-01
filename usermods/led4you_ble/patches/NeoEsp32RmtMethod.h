/*-------------------------------------------------------------------------
NeoPixel library helper functions for Esp32.

A BIG thanks to Andreas Merkle for the investigation and implementation of
a workaround to the GCC bug that drops method attributes from template methods 

Written by Michael C. Miller.

I invest time and resources providing this open source code,
please support me by donating (see https://github.com/Makuna/NeoPixelBus)

-------------------------------------------------------------------------
This file is part of the Makuna/NeoPixelBus library.

NeoPixelBus is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

NeoPixelBus is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with NeoPixel.  If not, see
<http://www.gnu.org/licenses/>.
-------------------------------------------------------------------------*/

#pragma once

#ifdef ARDUINO_ARCH_ESP32

/*  General Reference documentation for the APIs used in this implementation
LOW LEVEL:  (what is actually used)
DOCS: https://docs.espressif.com/projects/esp-idf/en/latest/api-reference/peripherals/rmt.html
EXAMPLE: https://github.com/espressif/esp-idf/blob/826ff7186ae07dc81e960a8ea09ebfc5304bfb3b/examples/peripherals/rmt_tx/main/rmt_tx_main.c

HIGHER LEVEL:
NO TRANSLATE SUPPORT so this was not used
NOTE: https://github.com/espressif/arduino-esp32/commit/50d142950d229b8fabca9b749dc4a5f2533bc426
Esp32-hal-rmt.h
Esp32-hal-rmt.c
*/

extern "C"
{
#include <rom/gpio.h>
#include <driver/rmt.h>
#if defined(CONFIG_IDF_TARGET_ESP32C3) && defined(LED4YOU_BLE)
// LED4YOU (patch): on the ESP32-C3 the first LED output is sent with SPI + DMA instead of RMT.
// The RMT on the C3 holds only a few LEDs and needs an interrupt to refill it during every frame; with
// Bluetooth on (Wi-Fi modem sleep, radio interrupts, flash access) that interrupt comes late and LEDs get
// wrong data. SPI DMA streams the whole frame from RAM with no CPU help once started.
#include <driver/spi_master.h>
#include <esp_heap_caps.h>
#define L4Y_SPI_LEDS 1
inline bool& l4ySpiLedsBusy() { static bool busy = false; return busy; }
#include <driver/gpio.h>
#include <soc/gpio_struct.h>
#include <soc/gpio_sig_map.h>
#endif
}

#ifdef L4Y_SPI_LEDS
// LED4YOU (patch, firmware v96): 3 or 4 LED outputs on the ESP32-C3 all go out together over SPI in quad mode:
// the 4 SPI data lines (D, Q, WP, HD) each carry one output, from one DMA buffer, so no output uses the RMT
// (2 RMT outputs with half the memory each froze the LEDs while Bluetooth was on). One LED bit = 3 SPI clocks;
// in quad mode one clock carries one bit of every output: the first clock of a byte uses bits 7..4
// (HD, WP, Q, D), the second bits 3..0.
struct L4yQuadHub {
    int alive = 0;            // WS281x-type outputs that exist (all are made before the first one starts)
    int want = 0, lanes = 0;  // outputs on the quad SPI: expected, started
    uint8_t pins[4] = {255, 255, 255, 255};
    size_t maxData = 0;       // biggest output, in data bytes
    uint8_t* buf = nullptr;   // DMA buffer: reset (low) slots, then 3 slots per LED data bit, 2 slots per byte
    size_t len = 0, lead = 0; // bytes; reset slots at the start
    uint32_t slotNs = 0; uint8_t ones0 = 1, ones1 = 2; uint32_t resetNs = 0;
    spi_device_handle_t dev = nullptr;
    spi_transaction_t t;
    bool pending = false, failed = false;
    bool wait(uint32_t ms) {
        if (!pending) return true;
        spi_transaction_t* r;
        if (spi_device_get_trans_result(dev, &r, ms ? pdMS_TO_TICKS(ms) : 0) != ESP_OK) return false;
        pending = false;
        return true;
    }
    void stop() {
        if (dev) { wait(1000); spi_bus_remove_device(dev); spi_bus_free(SPI2_HOST); dev = nullptr; }
        for (int i = 0; i < 4; i++) if (pins[i] != 255) { gpio_matrix_out(pins[i], SIG_GPIO_OUT_IDX, false, false); pinMode(pins[i], INPUT); pins[i] = 255; }
        heap_caps_free(buf); buf = nullptr; len = 0; maxData = 0; lanes = 0; want = 0; pending = false; failed = false;
        l4ySpiLedsBusy() = false;
    }
    bool start() {
        const size_t slots = lead + maxData * 24 + 16;
        len = (slots + 1) / 2;
        if (len * 8 > 262143) { failed = true; return false; }   // longer than one SPI transfer on the C3
        buf = static_cast<uint8_t*>(heap_caps_calloc(1, len, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL));
        if (!buf) { failed = true; return false; }
        spi_bus_config_t bus = {};
        bus.mosi_io_num = pins[0];
        bus.miso_io_num = pins[1];
        bus.quadwp_io_num = pins[2];
        bus.quadhd_io_num = want > 3 ? pins[3] : pins[2];   // 3 outputs: HD is set up on the WP pin, then taken off it below
        bus.sclk_io_num = -1;
        bus.max_transfer_sz = len;
        bus.flags = SPICOMMON_BUSFLAG_MASTER | SPICOMMON_BUSFLAG_GPIO_PINS;
        if (spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO) != ESP_OK) { heap_caps_free(buf); buf = nullptr; failed = true; return false; }
        spi_device_interface_config_t d = {};
        d.clock_speed_hz = 1000000000UL / slotNs;
        d.mode = 0;
        d.spics_io_num = -1;
        d.queue_size = 1;
        d.flags = SPI_DEVICE_HALFDUPLEX | SPI_DEVICE_NO_DUMMY;
        if (spi_bus_add_device(SPI2_HOST, &d, &dev) != ESP_OK) { dev = nullptr; spi_bus_free(SPI2_HOST); heap_caps_free(buf); buf = nullptr; failed = true; return false; }
        // each output pin: its SPI data line, always driven (also between frames, so the LEDs see a steady low)
        static const uint8_t sig[4] = { FSPID_OUT_IDX, FSPIQ_OUT_IDX, FSPIWP_OUT_IDX, FSPIHD_OUT_IDX };
        for (int i = 0; i < want; i++) {
            gpio_set_direction(static_cast<gpio_num_t>(pins[i]), GPIO_MODE_OUTPUT);
            gpio_matrix_out(pins[i], sig[i], false, false);
            GPIO.func_out_sel_cfg[pins[i]].oen_sel = 1;
        }
        return true;
    }
    // writes one output's LED data into its line of the DMA buffer
    void encode(int lane, const uint8_t* src, size_t n) {
        uint8_t* b = buf;
        const uint8_t mHi = 1u << (4 + lane), mLo = 1u << lane;
        size_t t = lead;
        const bool s1for0 = ones0 >= 2, s1for1 = ones1 >= 2, s2for1 = ones1 >= 3;
        for (size_t i = 0; i < n; i++) {
            const uint8_t v = src[i];
            for (int bit = 7; bit >= 0; bit--) {
                const bool one = (v >> bit) & 1;
                const bool sl[3] = { true, one ? s1for1 : s1for0, one && s2for1 };
                for (int k = 0; k < 3; k++, t++) {
                    uint8_t& c = b[t >> 1];
                    const uint8_t m = (t & 1) ? mLo : mHi;
                    if (sl[k]) c |= m; else c &= ~m;
                }
            }
        }
    }
};
inline L4yQuadHub& l4yHub() { static L4yQuadHub h; return h; }
#endif

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(4, 3, 0)
#define NEOPIXELBUS_RMT_INT_FLAGS (ESP_INTR_FLAG_LOWMED)
#else
#define NEOPIXELBUS_RMT_INT_FLAGS (ESP_INTR_FLAG_IRAM | ESP_INTR_FLAG_LEVEL1)
#endif

class NeoEsp32RmtSpeed
{
public:
    // ClkDiv of 2 provides for good resolution and plenty of reset resolution; but
    // a ClkDiv of 1 will provide enough space for the longest reset and does show
    // little better pulse accuracy
    const static uint8_t RmtClockDivider = 2; 

    inline constexpr static uint32_t FromNs(uint32_t ns)
    {
        return ns / NsPerRmtTick;
    }

protected:
    const static uint32_t RmtCpu = 80000000L; // 80 mhz RMT clock
    const static uint32_t NsPerSecond = 1000000000L;
    const static uint32_t RmtTicksPerSecond = (RmtCpu / RmtClockDivider);
    const static uint32_t NsPerRmtTick = (NsPerSecond / RmtTicksPerSecond); // about 25 

    static void IRAM_ATTR _translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num,
        const uint32_t rmtBit0,
        const uint32_t rmtBit1,
        const uint16_t rmtDurationReset);

};

class NeoEsp32RmtSpeedBase : public NeoEsp32RmtSpeed
{
public:
    // this is used rather than the rmt_item32_t as you can't correctly initialize
    // it as a static constexpr within the template
    inline constexpr static uint32_t Item32Val(uint16_t nsHigh, uint16_t nsLow)
    {
        return (FromNs(nsLow) << 16) | (1 << 15) | (FromNs(nsHigh));
    }

    const static rmt_idle_level_t IdleLevel = RMT_IDLE_LEVEL_LOW;
};

class NeoEsp32RmtInvertedSpeedBase : public NeoEsp32RmtSpeed
{
public:
    // this is used rather than the rmt_item32_t as you can't correctly initialize
    // it as a static constexpr within the template
    inline constexpr static uint32_t Item32Val(uint16_t nsHigh, uint16_t nsLow)
    {
        return (FromNs(nsLow) << 16) | (1 << 31) | (FromNs(nsHigh));
    }

    const static rmt_idle_level_t IdleLevel = RMT_IDLE_LEVEL_HIGH;
};

class NeoEsp32RmtSpeedWs2811 : public NeoEsp32RmtSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(300, 950); 
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(900, 350); 
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(300000); // 300us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtSpeedWs2812x : public NeoEsp32RmtSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(400, 850);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(800, 450);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(300000); // 300us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtSpeedWs2805 : public NeoEsp32RmtSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(300, 790);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(790, 300);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(300000); // spec is 280, intentionally longer for compatiblity use

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtSpeedSk6812 : public NeoEsp32RmtSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(400, 850); 
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(800, 450); 
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(80000); // 80us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

// normal is inverted signal
class NeoEsp32RmtSpeedTm1814 : public NeoEsp32RmtInvertedSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(360, 890);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(720, 530);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(200000); // 200us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

// normal is inverted signal
class NeoEsp32RmtSpeedTm1829 : public NeoEsp32RmtInvertedSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(300, 900);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(800, 400);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(200000); // 200us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

// normal is inverted signal
class NeoEsp32RmtSpeedTm1914 : public NeoEsp32RmtInvertedSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(360, 890);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(720, 530);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(200000); // 200us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtSpeed800Kbps : public NeoEsp32RmtSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(400, 850); 
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(800, 450); 
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(50000); // 50us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtSpeed400Kbps : public NeoEsp32RmtSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(800, 1700); 
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(1600, 900); 
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(50000); // 50us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtSpeedApa106 : public NeoEsp32RmtSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(350, 1350);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(1350, 350);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(50000); // 50us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtSpeedTx1812 : public NeoEsp32RmtSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(300, 600); 
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(600, 300); 
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(80000); // 80us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtSpeedGs1903 : public NeoEsp32RmtSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(300, 900);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(900, 300);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(40000); // 40us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtInvertedSpeedWs2811 : public NeoEsp32RmtInvertedSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(300, 950);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(900, 350);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(300000); // 300us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtInvertedSpeedWs2812x : public NeoEsp32RmtInvertedSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(400, 850);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(800, 450);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(300000); // 300us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtInvertedSpeedWs2805 : public NeoEsp32RmtInvertedSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(300, 790);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(790, 300);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(300000); // spec is 280, intentionally longer for compatiblity use

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtInvertedSpeedSk6812 : public NeoEsp32RmtInvertedSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(400, 850);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(800, 450);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(80000); // 80us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

// normal is inverted signal
class NeoEsp32RmtInvertedSpeedTm1814 : public NeoEsp32RmtSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(360, 890);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(720, 530);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(200000); // 200us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

// normal is inverted signal
class NeoEsp32RmtInvertedSpeedTm1829 : public NeoEsp32RmtSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(300, 900);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(800, 400);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(200000); // 200us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

// normal is inverted signal
class NeoEsp32RmtInvertedSpeedTm1914 : public NeoEsp32RmtSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(360, 890);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(720, 530);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(200000); // 200us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtInvertedSpeed800Kbps : public NeoEsp32RmtInvertedSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(400, 850);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(800, 450);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(50000); // 50us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtInvertedSpeed400Kbps : public NeoEsp32RmtInvertedSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(800, 1700);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(1600, 900);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(50000); // 50us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtInvertedSpeedApa106 : public NeoEsp32RmtInvertedSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(350, 1350);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(1350, 350);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(50000); // 50us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtInvertedSpeedTx1812 : public NeoEsp32RmtInvertedSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(300, 600); 
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(600, 300); 
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(80000); // 80us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtInvertedSpeedGs1903 : public NeoEsp32RmtInvertedSpeedBase
{
public:
    const static DRAM_ATTR uint32_t RmtBit0 = Item32Val(300, 900);
    const static DRAM_ATTR uint32_t RmtBit1 = Item32Val(900, 300);
    const static DRAM_ATTR uint16_t RmtDurationReset = FromNs(40000); // 40us

    static void IRAM_ATTR Translate(const void* src,
        rmt_item32_t* dest,
        size_t src_size,
        size_t wanted_num,
        size_t* translated_size,
        size_t* item_num);
};

class NeoEsp32RmtChannel0
{
public:
    NeoEsp32RmtChannel0() {};

    const static rmt_channel_t RmtChannelNumber = RMT_CHANNEL_0;
};

class NeoEsp32RmtChannel1
{
public:
    NeoEsp32RmtChannel1() {};

    const static rmt_channel_t RmtChannelNumber = RMT_CHANNEL_1;
};

class NeoEsp32RmtChannel2
{
public:
    NeoEsp32RmtChannel2() {};

    const static rmt_channel_t RmtChannelNumber = RMT_CHANNEL_2;
};

class NeoEsp32RmtChannel3
{
public:
    NeoEsp32RmtChannel3() {};

    const static rmt_channel_t RmtChannelNumber = RMT_CHANNEL_3;
};

#if !defined(CONFIG_IDF_TARGET_ESP32S2) && !defined(CONFIG_IDF_TARGET_ESP32C3) && !defined(CONFIG_IDF_TARGET_ESP32S3)

class NeoEsp32RmtChannel4
{
public:
    NeoEsp32RmtChannel4() {};

    const static rmt_channel_t RmtChannelNumber = RMT_CHANNEL_4;
};

class NeoEsp32RmtChannel5
{
public:
    NeoEsp32RmtChannel5() {};

    const static rmt_channel_t RmtChannelNumber = RMT_CHANNEL_5;
};

class NeoEsp32RmtChannel6
{
public:
    NeoEsp32RmtChannel6() {};

    const static rmt_channel_t RmtChannelNumber = RMT_CHANNEL_6;
};

class NeoEsp32RmtChannel7
{
public:
    NeoEsp32RmtChannel7() {};

    const static rmt_channel_t RmtChannelNumber = RMT_CHANNEL_7;
};

#endif

// dynamic channel support
class NeoEsp32RmtChannelN
{
public:
    NeoEsp32RmtChannelN(NeoBusChannel channel) :
        RmtChannelNumber(static_cast<rmt_channel_t>(channel))
    {
    }
    NeoEsp32RmtChannelN() = delete; // no default constructor

    const rmt_channel_t RmtChannelNumber;
};

template<typename T_SPEED, typename T_CHANNEL> class NeoEsp32RmtMethodBase
{
public:
    typedef NeoNoSettings SettingsObject;

    NeoEsp32RmtMethodBase(uint8_t pin, uint16_t pixelCount, size_t elementSize, size_t settingsSize)  :
        _sizeData(pixelCount * elementSize + settingsSize),
        _pin(pin)
    {
        construct();
    }

    NeoEsp32RmtMethodBase(uint8_t pin, uint16_t pixelCount, size_t elementSize, size_t settingsSize, NeoBusChannel channel) :
        _sizeData(pixelCount* elementSize + settingsSize),
        _pin(pin),
        _channel(channel)
    {
        construct();
    }

    ~NeoEsp32RmtMethodBase()
    {
#ifdef L4Y_SPI_LEDS
        if (_cand) l4yHub().alive--;
        if (_hubLane >= 0)
        {
            L4yQuadHub& h = l4yHub();
            h.wait(1000);
            if (--h.lanes <= 0) h.stop();
            free(_dataEditing);
            free(_dataSending);
            return;
        }
        if (_spiDev)
        {
            spiWait(1000);
            spi_bus_remove_device(_spiDev);
            spi_bus_free(SPI2_HOST);
            heap_caps_free(_spiBuf);
            l4ySpiLedsBusy() = false;
            gpio_matrix_out(_pin, SIG_GPIO_OUT_IDX, false, false);
            pinMode(_pin, INPUT);
            free(_dataEditing);
            free(_dataSending);
            return;
        }
#endif
        if (_rmtCh >= RMT_CHANNEL_MAX) { free(_dataEditing); free(_dataSending); return; }   // LED4YOU (patch): output with no RMT channel
        // wait until the last send finishes before destructing everything
        // arbitrary time out of 10 seconds
        ESP_ERROR_CHECK_WITHOUT_ABORT(rmt_wait_tx_done(_rmtCh, 10000 / portTICK_PERIOD_MS));

        ESP_ERROR_CHECK(rmt_driver_uninstall(_rmtCh));

        gpio_matrix_out(_pin, SIG_GPIO_OUT_IDX, false, false);
        pinMode(_pin, INPUT);

        free(_dataEditing);
        free(_dataSending);
    }

    bool IsReadyToUpdate() const
    {
#ifdef L4Y_SPI_LEDS
        if (_hubLane >= 0) return l4yHub().wait(0);
        if (_spiDev) return spiWait(0);
#endif
        if (_rmtCh >= RMT_CHANNEL_MAX) return true;
        return rmt_wait_tx_done(_rmtCh, 0) == ESP_OK;   // LED4YOU (patch): no logging of the normal "still sending" timeout
    }

    void Initialize()
    {
#ifdef L4Y_SPI_LEDS
        {
            // 3 or 4 WS281x-type outputs: all of them on the quad SPI (all outputs are made before the first starts)
            L4yQuadHub& h = l4yHub();
            if (_cand && h.alive >= 3 && !h.failed && !h.dev && h.lanes < 4)
            {
                if (h.lanes == 0) {
                    h.want = h.alive > 4 ? 4 : h.alive;
                    const uint32_t tickNs = 1000000000UL / (80000000UL / T_SPEED::RmtClockDivider);
                    const uint32_t h0 = (T_SPEED::RmtBit0 & 0x7fff) * tickNs, l0 = ((T_SPEED::RmtBit0 >> 16) & 0x7fff) * tickNs;
                    const uint32_t h1 = (T_SPEED::RmtBit1 & 0x7fff) * tickNs;
                    h.slotNs = (h0 + l0) / 3;
                    uint32_t o0 = (h0 + h.slotNs / 2) / h.slotNs, o1 = (h1 + h.slotNs / 2) / h.slotNs;
                    if (o0 < 1) o0 = 1;
                    if (o1 > 2) o1 = 2;
                    if (o1 <= o0) { o0 = 1; o1 = 2; }
                    h.ones0 = o0; h.ones1 = o1;
                    h.resetNs = (uint32_t)T_SPEED::RmtDurationReset * tickNs;
                    h.lead = ((h.resetNs + h.slotNs - 1) / h.slotNs + 8) & ~1u;   // reset time in slots, even
                }
                _hubLane = h.lanes++;
                h.pins[_hubLane] = _pin;
                if (_sizeData > h.maxData) h.maxData = _sizeData;
                if (h.lanes == h.want) h.start();
                l4ySpiLedsBusy() = true;   // the SPI is taken: any other output uses the RMT
                return;
            }
        }
        if (T_SPEED::IdleLevel == RMT_IDLE_LEVEL_LOW && !l4ySpiLedsBusy() && spiInit()) return;
#endif
        rmt_config_t config = {};

        config.rmt_mode = RMT_MODE_TX;
#if defined(CONFIG_IDF_TARGET_ESP32C3) && defined(LED4YOU_BLE)
        // LED4YOU (patch): the first output went to SPI, so RMT channel 0 is free: the second output (channel 1)
        // takes channel 0 and both RMT memory blocks
        if (l4ySpiLedsBusy() && _rmtCh >= RMT_CHANNEL_1 && _rmtCh <= RMT_CHANNEL_2) _rmtCh = static_cast<rmt_channel_t>(_rmtCh - 1);
        if (_rmtCh > RMT_CHANNEL_1) { _rmtCh = RMT_CHANNEL_MAX; return; }   // the C3 has only 2 RMT outputs: no LEDs here
        // a second RMT output (test mode: 3rd LED output) needs the memory block that channel 0 borrowed: give it back first
        if (_rmtCh == RMT_CHANNEL_1)
        {
            rmt_wait_tx_done(RMT_CHANNEL_0, pdMS_TO_TICKS(100));
            rmt_set_mem_block_num(RMT_CHANNEL_0, 1);
        }
#endif
        config.channel = _rmtCh;
        config.gpio_num = static_cast<gpio_num_t>(_pin);
#if defined(CONFIG_IDF_TARGET_ESP32C3) && defined(LED4YOU_BLE)
        // LED4YOU (patch): one output on the C3 uses both RMT memory blocks, so the refill interrupt comes half as
        // often and Bluetooth/Wi-Fi interrupts no longer starve it (wrong colours on some LEDs)
        config.mem_block_num = (_rmtCh == RMT_CHANNEL_0) ? 2 : 1;   // a later 3rd output takes the 2nd block back (above)
#else
        config.mem_block_num = 1;
#endif
        config.tx_config.loop_en = false;
        
        config.tx_config.idle_output_en = true;
        config.tx_config.idle_level = T_SPEED::IdleLevel;

        config.tx_config.carrier_en = false;
        config.tx_config.carrier_level = RMT_CARRIER_LEVEL_LOW;

        config.clk_div = T_SPEED::RmtClockDivider;

        ESP_ERROR_CHECK(rmt_config(&config));
        ESP_ERROR_CHECK(rmt_driver_install(_rmtCh, 0, NEOPIXELBUS_RMT_INT_FLAGS));
        ESP_ERROR_CHECK(rmt_translator_init(_rmtCh, T_SPEED::Translate));
    }

    void Update(bool maintainBufferConsistency)
    {
#ifdef L4Y_SPI_LEDS
        if (_hubLane >= 0)
        {
            L4yQuadHub& h = l4yHub();
            if (h.dev && h.wait(1000))
            {
                h.encode(_hubLane, _dataEditing, _sizeData);
                if (_hubLane == h.lanes - 1)   // the last output of the frame sends all of them
                {
                    memset(&h.t, 0, sizeof(h.t));
                    h.t.length = h.len * 8;
                    h.t.tx_buffer = h.buf;
                    h.t.flags = SPI_TRANS_MODE_QIO;
                    if (spi_device_queue_trans(h.dev, &h.t, 0) == ESP_OK) h.pending = true;
                }
            }
            if (maintainBufferConsistency) memcpy(_dataSending, _dataEditing, _sizeData);
            std::swap(_dataSending, _dataEditing);
            return;
        }
        if (_spiDev)
        {
            if (!spiWait(1000)) return;     // last frame still going (should never take this long)
            spiEncode(_dataEditing);         // the DMA buffer gets its own copy, sending never touches the pixel buffers
            memset(&_spiT, 0, sizeof(_spiT));
            _spiT.length = _spiLen * 8;
            _spiT.tx_buffer = _spiBuf;
            if (spi_device_queue_trans(_spiDev, &_spiT, 0) == ESP_OK) _spiPending = true;
            if (maintainBufferConsistency) memcpy(_dataSending, _dataEditing, _sizeData);
            std::swap(_dataSending, _dataEditing);
            return;
        }
#endif
        if (_rmtCh >= RMT_CHANNEL_MAX) return;   // LED4YOU (patch): output with no RMT channel
        // wait for not actively sending data
        // this will time out at 10 seconds, an arbitrarily long period of time
        // and do nothing if this happens
        if (ESP_OK == ESP_ERROR_CHECK_WITHOUT_ABORT(rmt_wait_tx_done(_rmtCh, 10000 / portTICK_PERIOD_MS)))
        {
            // now start the RMT transmit with the editing buffer before we swap
            ESP_ERROR_CHECK_WITHOUT_ABORT(rmt_write_sample(_rmtCh, _dataEditing, _sizeData, false));

            if (maintainBufferConsistency)
            {
                // copy editing to sending,
                // this maintains the contract that "colors present before will
                // be the same after", otherwise GetPixelColor will be inconsistent
                memcpy(_dataSending, _dataEditing, _sizeData);
            }

            // swap so the user can modify without affecting the async operation
            std::swap(_dataSending, _dataEditing);
        }
    }

    bool AlwaysUpdate()
    {
        // this method requires update to be called only if changes to buffer
#ifdef L4Y_SPI_LEDS
        return _hubLane >= 0;   // LED4YOU (patch): on the quad SPI the last output sends all of them every frame
#endif
        return false;
    }

    bool SwapBuffers()
    {
        std::swap(_dataSending, _dataEditing);
        return true;
    }

    uint8_t* getData() const
    {
        return _dataEditing;
    };

    size_t getDataSize() const
    {
        return _sizeData;
    }

    void applySettings([[maybe_unused]] const SettingsObject& settings)
    {
    }

private:
    const size_t  _sizeData;      // Size of '_data*' buffers 
    const uint8_t _pin;            // output pin number
    const T_CHANNEL _channel; // holds instance for multi channel support
    rmt_channel_t _rmtCh;     // LED4YOU (patch): RMT channel really used (the C3's 2nd output moves to channel 0, see Initialize)

    // Holds data stream which include LED color values and other settings as needed
    uint8_t*  _dataEditing;   // exposed for get and set
    uint8_t*  _dataSending;   // used for async send using RMT


#ifdef L4Y_SPI_LEDS
    bool _cand = false;       // WS281x-type output (data idles low): can go on the SPI
    int _hubLane = -1;        // line on the quad SPI, or -1
    spi_device_handle_t _spiDev = nullptr;
    uint8_t* _spiBuf = nullptr;      // DMA buffer: reset (low) bytes, then 3 SPI bits per LED data bit
    size_t _spiLen = 0;
    size_t _spiLead = 0;
    uint8_t _ones0 = 1, _ones1 = 2;  // how many of the 3 SPI bits are high for a 0 bit and for a 1 bit
    mutable bool _spiPending = false;
    spi_transaction_t _spiT;

    bool spiWait(uint32_t ms) const
    {
        if (!_spiPending) return true;
        spi_transaction_t* r;
        if (spi_device_get_trans_result(_spiDev, &r, ms ? pdMS_TO_TICKS(ms) : 0) != ESP_OK) return false;
        _spiPending = false;
        return true;
    }

    bool spiInit()
    {
        const uint32_t tickNs = 1000000000UL / (80000000UL / T_SPEED::RmtClockDivider);
        const uint32_t h0 = (T_SPEED::RmtBit0 & 0x7fff) * tickNs, l0 = ((T_SPEED::RmtBit0 >> 16) & 0x7fff) * tickNs;
        const uint32_t h1 = (T_SPEED::RmtBit1 & 0x7fff) * tickNs;
        const uint32_t slot = (h0 + l0) / 3;          // one LED bit = 3 SPI bits (WS2812: 2.4 MHz, 0 = 100, 1 = 110)
        if (slot == 0) return false;
        uint32_t o0 = (h0 + slot / 2) / slot, o1 = (h1 + slot / 2) / slot;
        if (o0 < 1) o0 = 1;
        if (o1 > 2) o1 = 2;
        if (o1 <= o0) { o0 = 1; o1 = 2; }
        _ones0 = o0; _ones1 = o1;
        const uint32_t resetNs = (uint32_t)T_SPEED::RmtDurationReset * tickNs;
        _spiLead = (resetNs + 8 * slot - 1) / (8 * slot) + 2;
        _spiLen = _spiLead + _sizeData * 3;
        if (_spiLen * 8 > 262143) return false;     // longer than one SPI transfer on the C3: use RMT
        _spiBuf = static_cast<uint8_t*>(heap_caps_calloc(1, _spiLen, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL));
        if (!_spiBuf) return false;
        spi_bus_config_t bus = {};
        bus.mosi_io_num = _pin;
        bus.miso_io_num = -1;
        bus.sclk_io_num = -1;
        bus.quadwp_io_num = -1;
        bus.quadhd_io_num = -1;
        bus.max_transfer_sz = _spiLen;
        if (spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO) != ESP_OK) { heap_caps_free(_spiBuf); _spiBuf = nullptr; return false; }
        spi_device_interface_config_t dev = {};
        dev.clock_speed_hz = 1000000000UL / slot;
        dev.mode = 0;
        dev.spics_io_num = -1;
        dev.queue_size = 1;
        dev.flags = SPI_DEVICE_NO_DUMMY;
        if (spi_bus_add_device(SPI2_HOST, &dev, &_spiDev) != ESP_OK)
        {
            _spiDev = nullptr;
            spi_bus_free(SPI2_HOST);
            heap_caps_free(_spiBuf); _spiBuf = nullptr;
            return false;
        }
        l4ySpiLedsBusy() = true;
        return true;
    }

    void spiEncode(const uint8_t* src)
    {
        const uint32_t p0 = (_ones0 == 1) ? 0b100 : 0b110, p1 = (_ones1 == 2) ? 0b110 : 0b111;
        uint8_t* d = _spiBuf + _spiLead;
        for (size_t i = 0; i < _sizeData; i++)
        {
            const uint8_t b = src[i];
            uint32_t v = 0;
            for (int bit = 7; bit >= 0; bit--) v = (v << 3) | ((b >> bit) & 1 ? p1 : p0);
            *d++ = v >> 16; *d++ = v >> 8; *d++ = v;
        }
    }
#endif

    void construct()
    {
#ifdef L4Y_SPI_LEDS
        _cand = T_SPEED::IdleLevel == RMT_IDLE_LEVEL_LOW;
        if (_cand) l4yHub().alive++;
#endif
        _rmtCh = static_cast<rmt_channel_t>(_channel.RmtChannelNumber);
        _dataEditing = static_cast<uint8_t*>(malloc(_sizeData));
        // data cleared later in Begin()

        _dataSending = static_cast<uint8_t*>(malloc(_sizeData));
        // no need to initialize it, it gets overwritten on every send
    }
};

// normal
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2811, NeoEsp32RmtChannelN> NeoEsp32RmtNWs2811Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannelN> NeoEsp32RmtNWs2812xMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannelN> NeoEsp32RmtNWs2816Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2805, NeoEsp32RmtChannelN> NeoEsp32RmtNWs2805Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedSk6812, NeoEsp32RmtChannelN> NeoEsp32RmtNSk6812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1814, NeoEsp32RmtChannelN> NeoEsp32RmtNTm1814Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1829, NeoEsp32RmtChannelN> NeoEsp32RmtNTm1829Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1914, NeoEsp32RmtChannelN> NeoEsp32RmtNTm1914Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedApa106, NeoEsp32RmtChannelN> NeoEsp32RmtNApa106Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTx1812, NeoEsp32RmtChannelN> NeoEsp32RmtNTx1812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedGs1903, NeoEsp32RmtChannelN> NeoEsp32RmtNGs1903Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed800Kbps, NeoEsp32RmtChannelN> NeoEsp32RmtN800KbpsMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed400Kbps, NeoEsp32RmtChannelN> NeoEsp32RmtN400KbpsMethod;
typedef NeoEsp32RmtNWs2805Method NeoEsp32RmtNWs2814Method;

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2811, NeoEsp32RmtChannel0> NeoEsp32Rmt0Ws2811Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel0> NeoEsp32Rmt0Ws2812xMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel0> NeoEsp32Rmt0Ws2816Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2805, NeoEsp32RmtChannel0> NeoEsp32Rmt0Ws2805Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedSk6812, NeoEsp32RmtChannel0> NeoEsp32Rmt0Sk6812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1814, NeoEsp32RmtChannel0> NeoEsp32Rmt0Tm1814Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1829, NeoEsp32RmtChannel0> NeoEsp32Rmt0Tm1829Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1914, NeoEsp32RmtChannel0> NeoEsp32Rmt0Tm1914Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedApa106, NeoEsp32RmtChannel0> NeoEsp32Rmt0Apa106Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTx1812, NeoEsp32RmtChannel0> NeoEsp32Rmt0Tx1812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedGs1903, NeoEsp32RmtChannel0> NeoEsp32Rmt0Gs1903Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed800Kbps, NeoEsp32RmtChannel0> NeoEsp32Rmt0800KbpsMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed400Kbps, NeoEsp32RmtChannel0> NeoEsp32Rmt0400KbpsMethod;
typedef NeoEsp32Rmt0Ws2805Method NeoEsp32Rmt0Ws2814Method;

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2811, NeoEsp32RmtChannel1> NeoEsp32Rmt1Ws2811Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel1> NeoEsp32Rmt1Ws2812xMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel1> NeoEsp32Rmt1Ws2816Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2805, NeoEsp32RmtChannel1> NeoEsp32Rmt1Ws2805Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedSk6812, NeoEsp32RmtChannel1> NeoEsp32Rmt1Sk6812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1814, NeoEsp32RmtChannel1> NeoEsp32Rmt1Tm1814Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1829, NeoEsp32RmtChannel1> NeoEsp32Rmt1Tm1829Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1914, NeoEsp32RmtChannel1> NeoEsp32Rmt1Tm1914Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedApa106, NeoEsp32RmtChannel1> NeoEsp32Rmt1Apa106Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTx1812, NeoEsp32RmtChannel1> NeoEsp32Rmt1Tx1812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedGs1903, NeoEsp32RmtChannel1> NeoEsp32Rmt1Gs1903Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed800Kbps, NeoEsp32RmtChannel1> NeoEsp32Rmt1800KbpsMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed400Kbps, NeoEsp32RmtChannel1> NeoEsp32Rmt1400KbpsMethod;
typedef NeoEsp32Rmt1Ws2805Method NeoEsp32Rmt1Ws2814Method;

#if !defined(CONFIG_IDF_TARGET_ESP32C3)

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2811, NeoEsp32RmtChannel2> NeoEsp32Rmt2Ws2811Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel2> NeoEsp32Rmt2Ws2812xMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel2> NeoEsp32Rmt2Ws2816Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2805, NeoEsp32RmtChannel2> NeoEsp32Rmt2Ws2805Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedSk6812, NeoEsp32RmtChannel2>  NeoEsp32Rmt2Sk6812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1814, NeoEsp32RmtChannel2> NeoEsp32Rmt2Tm1814Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1829, NeoEsp32RmtChannel2> NeoEsp32Rmt2Tm1829Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1914, NeoEsp32RmtChannel2> NeoEsp32Rmt2Tm1914Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedApa106, NeoEsp32RmtChannel2> NeoEsp32Rmt2Apa106Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTx1812, NeoEsp32RmtChannel2> NeoEsp32Rmt2Tx1812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedGs1903, NeoEsp32RmtChannel2> NeoEsp32Rmt2Gs1903Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed800Kbps, NeoEsp32RmtChannel2> NeoEsp32Rmt2800KbpsMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed400Kbps, NeoEsp32RmtChannel2> NeoEsp32Rmt2400KbpsMethod;
typedef NeoEsp32Rmt2Ws2805Method NeoEsp32Rmt2Ws2814Method;

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2811, NeoEsp32RmtChannel3> NeoEsp32Rmt3Ws2811Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel3> NeoEsp32Rmt3Ws2812xMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel3> NeoEsp32Rmt3Ws2816Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2805, NeoEsp32RmtChannel3> NeoEsp32Rmt3Ws2805Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedSk6812, NeoEsp32RmtChannel3>  NeoEsp32Rmt3Sk6812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1814, NeoEsp32RmtChannel3> NeoEsp32Rmt3Tm1814Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1829, NeoEsp32RmtChannel3> NeoEsp32Rmt3Tm1829Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1914, NeoEsp32RmtChannel3> NeoEsp32Rmt3Tm1914Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedApa106, NeoEsp32RmtChannel3> NeoEsp32Rmt3Apa106Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTx1812, NeoEsp32RmtChannel3> NeoEsp32Rmt3Tx1812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedGs1903, NeoEsp32RmtChannel3> NeoEsp32Rmt3Gs1903Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed800Kbps, NeoEsp32RmtChannel3> NeoEsp32Rmt3800KbpsMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed400Kbps, NeoEsp32RmtChannel3> NeoEsp32Rmt3400KbpsMethod;
typedef NeoEsp32Rmt3Ws2805Method NeoEsp32Rmt3Ws2814Method;

#if !defined(CONFIG_IDF_TARGET_ESP32S2) && !defined(CONFIG_IDF_TARGET_ESP32S3) 

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2811, NeoEsp32RmtChannel4> NeoEsp32Rmt4Ws2811Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel4> NeoEsp32Rmt4Ws2812xMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel4> NeoEsp32Rmt4Ws2816Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2805, NeoEsp32RmtChannel4> NeoEsp32Rmt4Ws2805Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedSk6812, NeoEsp32RmtChannel4>  NeoEsp32Rmt4Sk6812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1814, NeoEsp32RmtChannel4> NeoEsp32Rmt4Tm1814Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1829, NeoEsp32RmtChannel4> NeoEsp32Rmt4Tm1829Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1914, NeoEsp32RmtChannel4> NeoEsp32Rmt4Tm1914Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedApa106, NeoEsp32RmtChannel4> NeoEsp32Rmt4Apa106Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTx1812, NeoEsp32RmtChannel4> NeoEsp32Rmt4Tx1812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedGs1903, NeoEsp32RmtChannel4> NeoEsp32Rmt4Gs1903Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed800Kbps, NeoEsp32RmtChannel4> NeoEsp32Rmt4800KbpsMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed400Kbps, NeoEsp32RmtChannel4> NeoEsp32Rmt4400KbpsMethod;
typedef NeoEsp32Rmt4Ws2805Method NeoEsp32Rmt4Ws2814Method;

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2811, NeoEsp32RmtChannel5> NeoEsp32Rmt5Ws2811Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel5> NeoEsp32Rmt5Ws2812xMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel5> NeoEsp32Rmt5Ws2816Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2805, NeoEsp32RmtChannel5> NeoEsp32Rmt5Ws2805Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedSk6812, NeoEsp32RmtChannel5>  NeoEsp32Rmt5Sk6812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1814, NeoEsp32RmtChannel5> NeoEsp32Rmt5Tm1814Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1829, NeoEsp32RmtChannel5> NeoEsp32Rmt5Tm1829Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1914, NeoEsp32RmtChannel5> NeoEsp32Rmt5Tm1914Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedApa106, NeoEsp32RmtChannel5> NeoEsp32Rmt5Apa106Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTx1812, NeoEsp32RmtChannel5> NeoEsp32Rmt5Tx1812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedGs1903, NeoEsp32RmtChannel5> NeoEsp32Rmt5Gs1903Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed800Kbps, NeoEsp32RmtChannel5> NeoEsp32Rmt5800KbpsMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed400Kbps, NeoEsp32RmtChannel5> NeoEsp32Rmt5400KbpsMethod;
typedef NeoEsp32Rmt5Ws2805Method NeoEsp32Rmt5Ws2814Method;

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2811, NeoEsp32RmtChannel6> NeoEsp32Rmt6Ws2811Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel6> NeoEsp32Rmt6Ws2812xMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel6> NeoEsp32Rmt6Ws2816Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2805, NeoEsp32RmtChannel6> NeoEsp32Rmt6Ws2805Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedSk6812, NeoEsp32RmtChannel6>  NeoEsp32Rmt6Sk6812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1814, NeoEsp32RmtChannel6> NeoEsp32Rmt6Tm1814Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1829, NeoEsp32RmtChannel6> NeoEsp32Rmt6Tm1829Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1914, NeoEsp32RmtChannel6> NeoEsp32Rmt6Tm1914Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedApa106, NeoEsp32RmtChannel6> NeoEsp32Rmt6Apa106Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTx1812, NeoEsp32RmtChannel6> NeoEsp32Rmt6Tx1812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedGs1903, NeoEsp32RmtChannel6> NeoEsp32Rmt6Gs1903Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed800Kbps, NeoEsp32RmtChannel6> NeoEsp32Rmt6800KbpsMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed400Kbps, NeoEsp32RmtChannel6> NeoEsp32Rmt6400KbpsMethod;
typedef NeoEsp32Rmt6Ws2805Method NeoEsp32Rmt6Ws2814Method;

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2811, NeoEsp32RmtChannel7> NeoEsp32Rmt7Ws2811Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel7> NeoEsp32Rmt7Ws2812xMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2812x, NeoEsp32RmtChannel7> NeoEsp32Rmt7Ws2816Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedWs2805, NeoEsp32RmtChannel7> NeoEsp32Rmt7Ws2805Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedSk6812, NeoEsp32RmtChannel7>  NeoEsp32Rmt7Sk6812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1814, NeoEsp32RmtChannel7> NeoEsp32Rmt7Tm1814Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1829, NeoEsp32RmtChannel7> NeoEsp32Rmt7Tm1829Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTm1914, NeoEsp32RmtChannel7> NeoEsp32Rmt7Tm1914Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedApa106, NeoEsp32RmtChannel7> NeoEsp32Rmt7Apa106Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedTx1812, NeoEsp32RmtChannel7> NeoEsp32Rmt7Tx1812Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeedGs1903, NeoEsp32RmtChannel7> NeoEsp32Rmt7Gs1903Method;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed800Kbps, NeoEsp32RmtChannel7> NeoEsp32Rmt7800KbpsMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtSpeed400Kbps, NeoEsp32RmtChannel7> NeoEsp32Rmt7400KbpsMethod;
typedef NeoEsp32Rmt7Ws2805Method NeoEsp32Rmt7Ws2814Method;

#endif // !defined(CONFIG_IDF_TARGET_ESP32S2) && !defined(CONFIG_IDF_TARGET_ESP32S3) 
#endif // !defined(CONFIG_IDF_TARGET_ESP32C3)

// inverted
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2811, NeoEsp32RmtChannelN> NeoEsp32RmtNWs2811InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannelN> NeoEsp32RmtNWs2812xInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannelN> NeoEsp32RmtNWs2816InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2805, NeoEsp32RmtChannelN> NeoEsp32RmtNWs2805InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedSk6812, NeoEsp32RmtChannelN> NeoEsp32RmtNSk6812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1814, NeoEsp32RmtChannelN> NeoEsp32RmtNTm1814InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1829, NeoEsp32RmtChannelN> NeoEsp32RmtNTm1829InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1914, NeoEsp32RmtChannelN> NeoEsp32RmtNTm1914InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedApa106, NeoEsp32RmtChannelN> NeoEsp32RmtNApa106InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTx1812, NeoEsp32RmtChannelN> NeoEsp32RmtNTx1812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedGs1903, NeoEsp32RmtChannelN> NeoEsp32RmtNGs1903InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed800Kbps, NeoEsp32RmtChannelN> NeoEsp32RmtN800KbpsInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed400Kbps, NeoEsp32RmtChannelN> NeoEsp32RmtN400KbpsInvertedMethod;
typedef NeoEsp32RmtNWs2805InvertedMethod NeoEsp32RmtNWs2814InvertedMethod;

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2811, NeoEsp32RmtChannel0> NeoEsp32Rmt0Ws2811InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel0> NeoEsp32Rmt0Ws2812xInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel0> NeoEsp32Rmt0Ws2816InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2805, NeoEsp32RmtChannel0> NeoEsp32Rmt0Ws2805InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedSk6812, NeoEsp32RmtChannel0> NeoEsp32Rmt0Sk6812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1814, NeoEsp32RmtChannel0> NeoEsp32Rmt0Tm1814InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1829, NeoEsp32RmtChannel0> NeoEsp32Rmt0Tm1829InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1914, NeoEsp32RmtChannel0> NeoEsp32Rmt0Tm1914InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedApa106, NeoEsp32RmtChannel0> NeoEsp32Rmt0Apa106InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTx1812, NeoEsp32RmtChannel0> NeoEsp32Rmt0Tx1812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedGs1903, NeoEsp32RmtChannel0> NeoEsp32Rmt0Gs1903InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed800Kbps, NeoEsp32RmtChannel0> NeoEsp32Rmt0800KbpsInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed400Kbps, NeoEsp32RmtChannel0> NeoEsp32Rmt0400KbpsInvertedMethod;
typedef NeoEsp32Rmt0Ws2805InvertedMethod NeoEsp32Rmt0Ws2814InvertedMethod;

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2811, NeoEsp32RmtChannel1> NeoEsp32Rmt1Ws2811InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel1> NeoEsp32Rmt1Ws2812xInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel1> NeoEsp32Rmt1Ws2816InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2805, NeoEsp32RmtChannel1> NeoEsp32Rmt1Ws2805InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedSk6812, NeoEsp32RmtChannel1> NeoEsp32Rmt1Sk6812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1814, NeoEsp32RmtChannel1> NeoEsp32Rmt1Tm1814InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1829, NeoEsp32RmtChannel1> NeoEsp32Rmt1Tm1829InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1914, NeoEsp32RmtChannel1> NeoEsp32Rmt1Tm1914InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedApa106, NeoEsp32RmtChannel1> NeoEsp32Rmt1Apa106InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTx1812, NeoEsp32RmtChannel1> NeoEsp32Rmt1Tx1812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedGs1903, NeoEsp32RmtChannel1> NeoEsp32Rmt1Gs1903InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed800Kbps, NeoEsp32RmtChannel1> NeoEsp32Rmt1800KbpsInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed400Kbps, NeoEsp32RmtChannel1> NeoEsp32Rmt1400KbpsInvertedMethod;
typedef NeoEsp32Rmt1Ws2805InvertedMethod NeoEsp32Rmt1Ws2814InvertedMethod;

#if !defined(CONFIG_IDF_TARGET_ESP32C3)

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2811, NeoEsp32RmtChannel2> NeoEsp32Rmt2Ws2811InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel2> NeoEsp32Rmt2Ws2812xInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel2> NeoEsp32Rmt2Ws2816InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2805, NeoEsp32RmtChannel2> NeoEsp32Rmt2Ws2805InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedSk6812, NeoEsp32RmtChannel2>  NeoEsp32Rmt2Sk6812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1814, NeoEsp32RmtChannel2> NeoEsp32Rmt2Tm1814InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1829, NeoEsp32RmtChannel2> NeoEsp32Rmt2Tm1829InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1914, NeoEsp32RmtChannel2> NeoEsp32Rmt2Tm1914InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedApa106, NeoEsp32RmtChannel2> NeoEsp32Rmt2Apa106InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTx1812, NeoEsp32RmtChannel2> NeoEsp32Rmt2Tx1812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedGs1903, NeoEsp32RmtChannel2> NeoEsp32Rmt2Gs1903InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed800Kbps, NeoEsp32RmtChannel2> NeoEsp32Rmt2800KbpsInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed400Kbps, NeoEsp32RmtChannel2> NeoEsp32Rmt2400KbpsInvertedMethod;
typedef NeoEsp32Rmt2Ws2805InvertedMethod NeoEsp32Rmt2Ws2814InvertedMethod;

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2811, NeoEsp32RmtChannel3> NeoEsp32Rmt3Ws2811InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel3> NeoEsp32Rmt3Ws2812xInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2805, NeoEsp32RmtChannel3> NeoEsp32Rmt3Ws2805InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel3> NeoEsp32Rmt3Ws2816InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedSk6812, NeoEsp32RmtChannel3>  NeoEsp32Rmt3Sk6812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1814, NeoEsp32RmtChannel3> NeoEsp32Rmt3Tm1814InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1829, NeoEsp32RmtChannel3> NeoEsp32Rmt3Tm1829InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1914, NeoEsp32RmtChannel3> NeoEsp32Rmt3Tm1914InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedApa106, NeoEsp32RmtChannel3> NeoEsp32Rmt3Apa106InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTx1812, NeoEsp32RmtChannel3> NeoEsp32Rmt3Tx1812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedGs1903, NeoEsp32RmtChannel3> NeoEsp32Rmt3Gs1903InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed800Kbps, NeoEsp32RmtChannel3> NeoEsp32Rmt3800KbpsInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed400Kbps, NeoEsp32RmtChannel3> NeoEsp32Rmt3400KbpsInvertedMethod;
typedef NeoEsp32Rmt3Ws2805InvertedMethod NeoEsp32Rmt3Ws2814InvertedMethod;

#if !defined(CONFIG_IDF_TARGET_ESP32S2) && !defined(CONFIG_IDF_TARGET_ESP32S3)

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2811, NeoEsp32RmtChannel4> NeoEsp32Rmt4Ws2811InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel4> NeoEsp32Rmt4Ws2812xInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel4> NeoEsp32Rmt4Ws2816InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2805, NeoEsp32RmtChannel4> NeoEsp32Rmt4Ws2805InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedSk6812, NeoEsp32RmtChannel4>  NeoEsp32Rmt4Sk6812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1814, NeoEsp32RmtChannel4> NeoEsp32Rmt4Tm1814InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1829, NeoEsp32RmtChannel4> NeoEsp32Rmt4Tm1829InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1914, NeoEsp32RmtChannel4> NeoEsp32Rmt4Tm1914InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedApa106, NeoEsp32RmtChannel4> NeoEsp32Rmt4Apa106InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTx1812, NeoEsp32RmtChannel4> NeoEsp32Rmt4Tx1812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedGs1903, NeoEsp32RmtChannel4> NeoEsp32Rmt4Gs1903InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed800Kbps, NeoEsp32RmtChannel4> NeoEsp32Rmt4800KbpsInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed400Kbps, NeoEsp32RmtChannel4> NeoEsp32Rmt4400KbpsInvertedMethod;
typedef NeoEsp32Rmt4Ws2805InvertedMethod NeoEsp32Rmt4Ws2814InvertedMethod;

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2811, NeoEsp32RmtChannel5> NeoEsp32Rmt5Ws2811InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel5> NeoEsp32Rmt5Ws2812xInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel5> NeoEsp32Rmt5Ws2816InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2805, NeoEsp32RmtChannel5> NeoEsp32Rmt5Ws2805InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedSk6812, NeoEsp32RmtChannel5>  NeoEsp32Rmt5Sk6812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1814, NeoEsp32RmtChannel5> NeoEsp32Rmt5Tm1814InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1829, NeoEsp32RmtChannel5> NeoEsp32Rmt5Tm1829InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1914, NeoEsp32RmtChannel5> NeoEsp32Rmt5Tm1914InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedApa106, NeoEsp32RmtChannel5> NeoEsp32Rmt5Apa106InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTx1812, NeoEsp32RmtChannel5> NeoEsp32Rmt5Tx1812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedGs1903, NeoEsp32RmtChannel5> NeoEsp32Rmt5Gs1903InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed800Kbps, NeoEsp32RmtChannel5> NeoEsp32Rmt5800KbpsInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed400Kbps, NeoEsp32RmtChannel5> NeoEsp32Rmt5400KbpsInvertedMethod;
typedef NeoEsp32Rmt5Ws2805InvertedMethod NeoEsp32Rmt5Ws2814InvertedMethod;

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2811, NeoEsp32RmtChannel6> NeoEsp32Rmt6Ws2811InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel6> NeoEsp32Rmt6Ws2812xInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel6> NeoEsp32Rmt6Ws2816InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2805, NeoEsp32RmtChannel6> NeoEsp32Rmt6Ws2805InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedSk6812, NeoEsp32RmtChannel6>  NeoEsp32Rmt6Sk6812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1814, NeoEsp32RmtChannel6> NeoEsp32Rmt6Tm1814InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1829, NeoEsp32RmtChannel6> NeoEsp32Rmt6Tm1829InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1914, NeoEsp32RmtChannel6> NeoEsp32Rmt6Tm1914InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedApa106, NeoEsp32RmtChannel6> NeoEsp32Rmt6Apa106InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTx1812, NeoEsp32RmtChannel6> NeoEsp32Rmt6Tx1812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedGs1903, NeoEsp32RmtChannel6> NeoEsp32Rmt6Gs1903InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed800Kbps, NeoEsp32RmtChannel6> NeoEsp32Rmt6800KbpsInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed400Kbps, NeoEsp32RmtChannel6> NeoEsp32Rmt6400KbpsInvertedMethod;
typedef NeoEsp32Rmt6Ws2805InvertedMethod NeoEsp32Rmt6Ws2814InvertedMethod;

typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2811, NeoEsp32RmtChannel7> NeoEsp32Rmt7Ws2811InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel7> NeoEsp32Rmt7Ws2812xInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2812x, NeoEsp32RmtChannel7> NeoEsp32Rmt7Ws2816InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedWs2805, NeoEsp32RmtChannel7> NeoEsp32Rmt7Ws2805InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedSk6812, NeoEsp32RmtChannel7>  NeoEsp32Rmt7Sk6812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1814, NeoEsp32RmtChannel7> NeoEsp32Rmt7Tm1814InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1829, NeoEsp32RmtChannel7> NeoEsp32Rmt7Tm1829InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTm1914, NeoEsp32RmtChannel7> NeoEsp32Rmt7Tm1914InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedApa106, NeoEsp32RmtChannel7> NeoEsp32Rmt7Apa106InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedTx1812, NeoEsp32RmtChannel7> NeoEsp32Rmt7Tx1812InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeedGs1903, NeoEsp32RmtChannel7> NeoEsp32Rmt7Gs1903InvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed800Kbps, NeoEsp32RmtChannel7> NeoEsp32Rmt7800KbpsInvertedMethod;
typedef NeoEsp32RmtMethodBase<NeoEsp32RmtInvertedSpeed400Kbps, NeoEsp32RmtChannel7> NeoEsp32Rmt7400KbpsInvertedMethod;
typedef NeoEsp32Rmt7Ws2805InvertedMethod NeoEsp32Rmt7Ws2814InvertedMethod;

#endif // !defined(CONFIG_IDF_TARGET_ESP32S2) && !defined(CONFIG_IDF_TARGET_ESP32S3) 
#endif // !defined(CONFIG_IDF_TARGET_ESP32C3)


#if defined(NEOPIXEL_ESP32_RMT_DEFAULT) || defined(CONFIG_IDF_TARGET_ESP32S2) || defined(CONFIG_IDF_TARGET_ESP32C3) || defined(CONFIG_IDF_TARGET_ESP32S3)

// Normally I2s method is the default, defining NEOPIXEL_ESP32_RMT_DEFAULT 
// will switch to use RMT as the default method
// The ESP32S2, ESP32S3, and ESP32C3 will always defualt to RMT

#if defined(CONFIG_IDF_TARGET_ESP32S2) || defined(CONFIG_IDF_TARGET_ESP32C3) || defined(CONFIG_IDF_TARGET_ESP32S3)

// RMT channel 1 method is the default method for ESP32S2, ESP32S3, and ESP32C3
typedef NeoEsp32Rmt1Ws2812xMethod NeoWs2813Method;
typedef NeoEsp32Rmt1Ws2812xMethod NeoWs2812xMethod;
typedef NeoEsp32Rmt1800KbpsMethod NeoWs2812Method;
typedef NeoEsp32Rmt1Ws2812xMethod NeoWs2811Method;
typedef NeoEsp32Rmt1Ws2812xMethod NeoWs2816Method;
typedef NeoEsp32Rmt1Ws2805Method NeoWs2805Method;
typedef NeoEsp32Rmt1Ws2814Method NeoWs2814Method;
typedef NeoEsp32Rmt1Sk6812Method NeoSk6812Method;
typedef NeoEsp32Rmt1Tm1814Method NeoTm1814Method;
typedef NeoEsp32Rmt1Tm1829Method NeoTm1829Method;
typedef NeoEsp32Rmt1Tm1914Method NeoTm1914Method;
typedef NeoEsp32Rmt1Sk6812Method NeoLc8812Method;
typedef NeoEsp32Rmt1Apa106Method NeoApa106Method;
typedef NeoEsp32Rmt1Tx1812Method NeoTx1812Method;
typedef NeoEsp32Rmt1Gs1903Method NeoGs1903Method;

typedef NeoEsp32Rmt1Ws2812xMethod Neo800KbpsMethod;
typedef NeoEsp32Rmt1400KbpsMethod Neo400KbpsMethod;

typedef NeoEsp32Rmt1Ws2812xInvertedMethod NeoWs2813InvertedMethod;
typedef NeoEsp32Rmt1Ws2812xInvertedMethod NeoWs2812xInvertedMethod;
typedef NeoEsp32Rmt1Ws2812xInvertedMethod NeoWs2811InvertedMethod;
typedef NeoEsp32Rmt1800KbpsInvertedMethod NeoWs2812InvertedMethod;
typedef NeoEsp32Rmt1Ws2812xInvertedMethod NeoWs2816InvertedMethod;
typedef NeoEsp32Rmt1Ws2805InvertedMethod NeoWs2805InvertedMethod;
typedef NeoEsp32Rmt1Ws2814InvertedMethod NeoWs2814InvertedMethod;
typedef NeoEsp32Rmt1Sk6812InvertedMethod NeoSk6812InvertedMethod;
typedef NeoEsp32Rmt1Tm1814InvertedMethod NeoTm1814InvertedMethod;
typedef NeoEsp32Rmt1Tm1829InvertedMethod NeoTm1829InvertedMethod;
typedef NeoEsp32Rmt1Tm1914InvertedMethod NeoTm1914InvertedMethod;
typedef NeoEsp32Rmt1Sk6812InvertedMethod NeoLc8812InvertedMethod;
typedef NeoEsp32Rmt1Apa106InvertedMethod NeoApa106InvertedMethod;
typedef NeoEsp32Rmt1Tx1812InvertedMethod NeoTx1812InvertedMethod;
typedef NeoEsp32Rmt1Gs1903InvertedMethod NeoGs1903InvertedMethod;

typedef NeoEsp32Rmt1Ws2812xInvertedMethod Neo800KbpsInvertedMethod;
typedef NeoEsp32Rmt1400KbpsInvertedMethod Neo400KbpsInvertedMethod;

#else // defined(CONFIG_IDF_TARGET_ESP32S2) || defined(CONFIG_IDF_TARGET_ESP32C3) || defined(CONFIG_IDF_TARGET_ESP32S3)

// RMT channel 6 method is the default method for Esp32
typedef NeoEsp32Rmt6Ws2812xMethod NeoWs2813Method;
typedef NeoEsp32Rmt6Ws2812xMethod NeoWs2812xMethod;
typedef NeoEsp32Rmt6800KbpsMethod NeoWs2812Method;
typedef NeoEsp32Rmt6Ws2812xMethod NeoWs2811Method;
typedef NeoEsp32Rmt6Ws2812xMethod NeoWs2816Method;
typedef NeoEsp32Rmt6Ws2805Method NeoWs2805Method;
typedef NeoEsp32Rmt6Ws2814Method NeoWs2814Method;
typedef NeoEsp32Rmt6Sk6812Method NeoSk6812Method;
typedef NeoEsp32Rmt6Tm1814Method NeoTm1814Method;
typedef NeoEsp32Rmt6Tm1829Method NeoTm1829Method;
typedef NeoEsp32Rmt6Tm1914Method NeoTm1914Method;
typedef NeoEsp32Rmt6Sk6812Method NeoLc8812Method;
typedef NeoEsp32Rmt6Apa106Method NeoApa106Method;
typedef NeoEsp32Rmt6Tx1812Method NeoTx1812Method;
typedef NeoEsp32Rmt6Gs1903Method NeoGs1903Method;

typedef NeoEsp32Rmt6Ws2812xMethod Neo800KbpsMethod;
typedef NeoEsp32Rmt6400KbpsMethod Neo400KbpsMethod;

typedef NeoEsp32Rmt6Ws2812xInvertedMethod NeoWs2813InvertedMethod;
typedef NeoEsp32Rmt6Ws2812xInvertedMethod NeoWs2812xInvertedMethod;
typedef NeoEsp32Rmt6Ws2812xInvertedMethod NeoWs2811InvertedMethod;
typedef NeoEsp32Rmt6800KbpsInvertedMethod NeoWs2812InvertedMethod;
typedef NeoEsp32Rmt6Ws2812xInvertedMethod NeoWs2816InvertedMethod;
typedef NeoEsp32Rmt6Ws2805InvertedMethod NeoWs2805InvertedMethod;
typedef NeoEsp32Rmt6Ws2814InvertedMethod NeoWs2814InvertedMethod;
typedef NeoEsp32Rmt6Sk6812InvertedMethod NeoSk6812InvertedMethod;
typedef NeoEsp32Rmt6Tm1814InvertedMethod NeoTm1814InvertedMethod;
typedef NeoEsp32Rmt6Tm1829InvertedMethod NeoTm1829InvertedMethod;
typedef NeoEsp32Rmt6Tm1914InvertedMethod NeoTm1914InvertedMethod;
typedef NeoEsp32Rmt6Sk6812InvertedMethod NeoLc8812InvertedMethod;
typedef NeoEsp32Rmt6Apa106InvertedMethod NeoApa106InvertedMethod;
typedef NeoEsp32Rmt6Tx1812InvertedMethod NeoTx1812InvertedMethod;
typedef NeoEsp32Rmt6Gs1903InvertedMethod NeoGs1903InvertedMethod;

typedef NeoEsp32Rmt6Ws2812xInvertedMethod Neo800KbpsInvertedMethod;
typedef NeoEsp32Rmt6400KbpsInvertedMethod Neo400KbpsInvertedMethod;

#endif // defined(CONFIG_IDF_TARGET_ESP32S2) || defined(CONFIG_IDF_TARGET_ESP32C3)

#endif // defined(NEOPIXEL_ESP32_RMT_DEFAULT) || defined(CONFIG_IDF_TARGET_ESP32S2) || defined(CONFIG_IDF_TARGET_ESP32C3)

#endif
