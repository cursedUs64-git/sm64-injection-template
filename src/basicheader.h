#ifndef _MARIOTEST_
#define _MARIOTEST_

#include <ultra64.h>
#include "sm64.h"
#include "audio/external.h"
#include "behavior_data.h"
#include "dialog_ids.h"
#include "engine/behavior_script.h"
#include "engine/math_util.h"
#include "engine/surface_collision.h"
#include "engine/surface_load.h"
#include "level_table.h"
#include "game/obj_behaviors.h"
#include "game/obj_behaviors_2.h"
#include "game/object_helpers.h"
#include "object_constants.h"
#include "game/object_list_processor.h"
#include "game/platform_displacement.h"
#include "game/rendering_graph_node.h"
#include "game/save_file.h"
#include "game/spawn_sound.h"
#include "game/mario_actions_cutscene.h"
#include "game/camera.h"
#include "game/area.h"
#include "game/level_update.h"
#include "engine/math_util.h"
#include "game/interaction.h"
#include "game/mario.h"
#include "game/mario_step.h"
#include "game/camera.h"
#include "game/save_file.h"
#include "audio/external.h"
#include "engine/graph_node.h"
#include "game/game_init.h"
#include "seq_ids.h"
#include "game/ingame_menu.h"
#include "game/memory.h"
#include "goddard/gd_types.h"
#include "audio/internal.h"
#include "buffers/framebuffers.h"
#include "buffers/zbuffer.h"
#include "geo_commands.h"
#include "level_commands.h"
#include "goddard/dynlist_proc.h"
#include "game/paintings.h"
#include "goddard/debug_utils.h"
#include "goddard/gd_memory.h"
#include "audio/load.h"

// one of some constants from:

// src/goddard/dynlist_proc.c
#define DYNOBJ_NAME_SIZE 8

// src/audio/external.c
#define MAX_CHANNELS_PER_SOUND_BANK 1

// externs for static stuff
#include "src.externs.h"
#include "actors.externs.h"


#endif // _MARIOTEST_
