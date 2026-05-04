.n64
.open ROM_IN, ROM_OUT, 0x00000000

/******************** Includes *****************************/
.include "asm/sections.asm"
.include "asm/symbols.asm"

/******************** Custom injection ********************/
.headersize SEC_CUSTOM_HEADERSIZE
.orga SEC_CUSTOM_ROM
.area SEC_CUSTOM_SIZE

// The separate load_patchable_table function for mario's animations
.importobj "obj/custom/mario_anim_load_patchable_table.o"

.headersize 0-orga() // the pointers are relative to the start of the animation because it's dynamic in RAM
.definelabel @anim_d1_start, orga()
.importobj "obj/anims/windemoAold.o"
.definelabel @anim_d1_size, orga()-@anim_d1_start

// After adding animations, go back to original headersize
.headersize SEC_CUSTOM_HEADERSIZE

// make a variable of struct type OffsetSizePair
.definelabel mario_patchable_table_TWO, org()
.word @anim_d1_start, @anim_d1_size

.endarea

/******************** Custom segment loader ********************/

.headersize SEC_MAIN_HEADERSIZE

// 0x40 bytes of free space because of unused functions (4 functions)
/* stub_debug_1 - stub_debug_4 */
.org 0x802ca370
.area 0x802ca3b0 - 0x802ca370, 0
.importobj "obj/loads/custom_loads.o" // function here performs DMA read from the ROM and allocates space in RAM, copying from ROM to RAM
.endarea

// Makes a change in setup_game_memory to also call custom_loads which contains the DMA read for custom space
/* setup_game_memory */
.org 0x80248964
.area 0x80248af0 - 0x80248964, 0
.importobj "obj/hooks/setup_game_memory.o"
.endarea

/******************** Function Replacement ********************/

.headersize SEC_MAIN_HEADERSIZE

/* for extra animations */
.org 0x802509EC // set_mario_animation
JAL     mario_anim_load_patchable_table // was the vanilla load_patchable_table function before
.org 0x80250B3C // set_mario_anim_with_accel
JAL     mario_anim_load_patchable_table // was the vanilla load_patchable_table function before

// replace animation with cahstom animation in cahstom patchable table (windemoAold)
/* act_star_dance */
.org 0x80258420
.area 0x802584dc - 0x80258420, 0
.importobj "obj/hooks/act_star_dance.o"
.endarea

.close
