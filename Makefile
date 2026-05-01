# SM64 Injection Template

include util.mk

# ----------------------------
# Paths / tools
# ----------------------------
SRC_ROOT_DIR    := src
OBJ_ROOT_DIR    := obj
TMP_DIR         := tmp
TOOLS_DIR       := tools
SM64TOOLS_DIR   := $(TOOLS_DIR)/sm64tools
RECOMP_CC_DIR   := $(TOOLS_DIR)/ido-static-recomp

CROSS_CC        := $(RECOMP_CC_DIR)/build/out/cc
ARMIPS          := $(TOOLS_DIR)/armips # God i need to update armips' code...
N64CKSUM        := $(SM64TOOLS_DIR)/n64cksum
PYTHON := python3 # Assuming python is called python3 in the host (python >=3 is necessary)
MINIFIND        := $(PYTHON) $(TOOLS_DIR)/util/minifind.py
GEN_ARMIPS_SYMS := $(PYTHON) $(TOOLS_DIR)/util/gen_armips_syms.py # this will be used in later revisions to generate definelabels for symbols that can be used by armips

ROM_IN          := baserom.us.z64
ROM_OUT         := patched.us.z64

# ----------------------------
# Auto-discover headers and sources
# ----------------------------

# Headers and include flags
HEADER_DIRS := $(shell $(MINIFIND) $(SRC_ROOT_DIR) -type f -name "*.h" | xargs -r -n1 dirname | sort -u)
ifeq ($(strip $(HEADER_DIRS)),)
  HEADER_DIRS := $(SRC_ROOT_DIR)
endif
INCLUDE_FLAGS := -Iinclude/sm64 -Iinclude/sm64/include -Iinclude/sm64/include/libc -Iinclude/sm64/src $(foreach d,$(HEADER_DIRS),-I$(d))

# Search C (and ASM) files to be compiled and also to sort recursive obj directories
CUSTOM_C_SRCS := $(filter-out %.inc.c, $(shell $(MINIFIND) $(SRC_ROOT_DIR) -type f -name "*.c"))
CUSTOM_ASM_SRCS := $(shell $(MINIFIND) $(SRC_ROOT_DIR) -type f \( -name "*.s" -o -name "*.S" -o -name "*.asm" \))
ASM_S_SRCS   := $(filter %.s,$(CUSTOM_ASM_SRCS))
ASM_S_CAP_SRCS := $(filter %.S,$(CUSTOM_ASM_SRCS))
ASM_ASM_SRCS := $(filter %.asm,$(CUSTOM_ASM_SRCS))

CUSTOM_OBJS := \
  $(patsubst $(SRC_ROOT_DIR)/%.c,$(OBJ_ROOT_DIR)/%.o,$(CUSTOM_C_SRCS)) \
  $(patsubst $(SRC_ROOT_DIR)/%.s,$(OBJ_ROOT_DIR)/%.o,$(ASM_S_SRCS)) \
  $(patsubst $(SRC_ROOT_DIR)/%.S,$(OBJ_ROOT_DIR)/%.o,$(ASM_S_CAP_SRCS)) \
  $(patsubst $(SRC_ROOT_DIR)/%.asm,$(OBJ_ROOT_DIR)/%.o,$(ASM_ASM_SRCS))

OBJ_DIRS := $(sort $(dir $(CUSTOM_OBJS)))

# ----------------------------
# Convert pictures to .inc.c
# ----------------------------
N64GRAPHICS := $(SM64TOOLS_DIR)/n64graphics

# Find all PNG files under src/
PNG_SRCS := $(shell $(MINIFIND) $(SRC_ROOT_DIR) -type f -name "*.png")
INC_C_SRCS := $(patsubst %.png,%.inc.c,$(PNG_SRCS))

# Conversion rule
%.inc.c: %.png $(N64GRAPHICS)
	@echo "Converting: $< -> $@"
	@$(N64GRAPHICS) -s u8 -i $@ -g $< -f $(lastword $(subst ., ,$(basename $<)))

# ----------------------------
# Flags
# ----------------------------
CFLAGS := $(INCLUDE_FLAGS) -O2 -G0 -Wo,-loopunroll,0 -non_shared -Wab,-r4300_mul -Xcpluscomm -signed -32 -nostdinc -DTARGET_N64 -D_LANGUAGE_C -mips2 -fullwarn
ARMIPSFLAGS := -sym $(TMP_DIR)/sym.txt -strequ ROM_IN $(ROM_IN) -strequ ROM_OUT $(ROM_OUT)

# ----------------------------
# Phony targets
# ----------------------------
.PHONY: all build tools obj_dirs inject clean distclean info default

# ----------------------------
# Default target
# ----------------------------
all: build inject

# ----------------------------
# Info
# ----------------------------
info:
	@echo "Found sources under src/:"
	@echo "  C files:            $(words $(CUSTOM_C_SRCS))"
	@echo "  ASM files:          $(words $(CUSTOM_ASM_SRCS))"
	@echo "  Object directories: $(words $(OBJ_DIRS))"

# ----------------------------
# Build target
# ----------------------------
$(CUSTOM_OBJS): $(INC_C_SRCS)
build: tools info obj_dirs $(CUSTOM_OBJS)
	@echo "Build finished successfully."

# ----------------------------
# Tools
# ----------------------------
tools:
	@echo "Building tools..."
	@$(MAKE) -C $(TOOLS_DIR) all > /dev/null
	@$(MAKE) -C $(SM64TOOLS_DIR) > /dev/null

# ----------------------------
# Create obj/ and its recursive directories
# ----------------------------
obj_dirs:
	@echo "Creating object directories..."
	@for f in $(CUSTOM_OBJS); do \
	  mkdir -p $$(dirname $$f); \
	done
	@mkdir -p $(TMP_DIR)

# ----------------------------
# Compile C files
# ----------------------------
$(OBJ_ROOT_DIR)/%.o: $(SRC_ROOT_DIR)/%.c | obj_dirs tools
	@echo "CC $< -> $@"
	@$(CROSS_CC) $(CFLAGS) -c $< -o $@

# ----------------------------
# Inject into the ROM
# ----------------------------
inject: $(ROM_IN) build
	@echo "Injecting into the ROM via armips"
	@$(ARMIPS) inject.asm -root . $(ARMIPSFLAGS)
	@$(N64CKSUM) $(ROM_OUT) $(ROM_OUT)
	@echo "Patched ROM ready: $(ROM_OUT)"

# ----------------------------
# Clean
# ----------------------------
clean:
	@rm -rf $(OBJ_ROOT_DIR) $(TMP_DIR) $(ROM_OUT)
	@$(MINIFIND) $(SRC_ROOT_DIR) -type f -name '*.*.inc.c' | xargs -r rm -f # this implies all picture stuff to end with *.(type of texture).inc.c
	@echo "Clean done."

distclean: clean
	@$(MAKE) -C $(TOOLS_DIR) clean
	@echo "Distclean done."

# ----------------------------
# Include dependencies
# ----------------------------
-include $(CUSTOM_OBJS:.o=.d)

