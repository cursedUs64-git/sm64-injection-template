#include "basicheader.h"

// NOTE: Make changes for these macros if using a compressed ROM as segment addresses may vary.

// comment load_segment and uncomment the other if needed. Might move these defines to armips?
// #define _segment2_mio0SegmentRomStart 0x00800000 // hacky solution with a mio0 stub header
#define _segment2_mio0SegmentRomEnd 0x0081bb64

#define _segment2_SegmentRomStart 0x00803156
#define _segment2_SegmentRomEnd _segment2_mio0SegmentRomEnd

// addresses resolved by armips, the linker
extern u8 _entrySegmentRomStart[];
extern u8 _entrySegmentRomEnd[];

extern void custom_loads(void);

// The vanilla function, except it has changed addresses for load_segment and also calls the custom_load function for performing DMA reads.
void setup_game_memory(void) {
    // UNUSED u8 filler[8]; // save space

    // Setup general Segment 0
    set_segment_base_addr(0, (void *) 0x80000000);
    // Create Mesg Queues
    osCreateMesgQueue(&gGfxVblankQueue, gGfxMesgBuf, ARRAY_COUNT(gGfxMesgBuf));
    osCreateMesgQueue(&gGameVblankQueue, gGameMesgBuf, ARRAY_COUNT(gGameMesgBuf));
    // Setup z buffer and framebuffer
    gPhysicalZBuffer = VIRTUAL_TO_PHYSICAL(gZBuffer);
    gPhysicalFramebuffers[0] = VIRTUAL_TO_PHYSICAL(gFramebuffer0);
    gPhysicalFramebuffers[1] = VIRTUAL_TO_PHYSICAL(gFramebuffer1);
    gPhysicalFramebuffers[2] = VIRTUAL_TO_PHYSICAL(gFramebuffer2);
    // Setup Mario Animations
    gMarioAnimsMemAlloc = main_pool_alloc(0x4000, MEMORY_POOL_LEFT);
    set_segment_base_addr(17 /* 0x11 */, (void *) gMarioAnimsMemAlloc);
    setup_dma_table_list(&gMarioAnimsBuf, gMarioAnims, gMarioAnimsMemAlloc);
    // Setup Demo Inputs List
    gDemoInputsMemAlloc = main_pool_alloc(0x800, MEMORY_POOL_LEFT);
    set_segment_base_addr(24, (void *) gDemoInputsMemAlloc);
    setup_dma_table_list(&gDemoInputsBuf, gDemoInputs, gDemoInputsMemAlloc);
    // Setup Level Script Entry
    load_segment(0x10, (void *)_entrySegmentRomStart, (void *)_entrySegmentRomEnd, MEMORY_POOL_LEFT);

    // Setup Segment 2 (Fonts, Text, etc)

    // CHANGE START
    // load_segment_decompress(2, (void *)_segment2_mio0SegmentRomStart, (void *)_segment2_mio0SegmentRomEnd); // uncommented because register A3 is not set
    load_segment(2, (void *)_segment2_SegmentRomStart, (void *)_segment2_SegmentRomEnd, MEMORY_POOL_LEFT);

    custom_loads();

    // CHANGE END
}
