#include "basicheader.h"

// Resolved addresses by the linker (armips)
extern u8 SEC_CUSTOM_RAM[];
extern u8 SEC_CUSTOM_ROM[];
extern u8 SEC_CUSTOM_SIZE[];

void custom_loads(void) {
    // Pointer casting to make the "arrays" able to operate arithmetically
    dma_read(/* dest */ SEC_CUSTOM_RAM, /* srcStart */ SEC_CUSTOM_ROM, /* srcEnd */ (u8 *)((u32)SEC_CUSTOM_ROM + (u32)SEC_CUSTOM_SIZE));
}
