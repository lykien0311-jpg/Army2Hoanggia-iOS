#pragma once
#include <stdint.h>

/* Build 269 GameCanvas keeps a reusable dialog at +0xc8 and the visible
 * dialog at +0x108. The loading dialog has no soft keys. The wrapped text
 * object distinguishes one use of that dialog from the next. */
static inline uintptr_t AGSpectatorWaitToken(void *canvas) {
    if (!canvas) return 0;
    uintptr_t *active = (uintptr_t *)((uint8_t *)canvas + 0x108);
    uintptr_t cached = *(uintptr_t *)((uint8_t *)canvas + 0xc8);
    if (!cached || __atomic_load_n(active, __ATOMIC_ACQUIRE) != cached) return 0;
    const uint8_t *dialog = (const uint8_t *)cached;
    if (*(const uintptr_t *)(dialog + 0x10) || *(const uintptr_t *)(dialog + 0x18) ||
        *(const uintptr_t *)(dialog + 0x20)) return 0;
    return *(const uintptr_t *)(dialog + 0x28);
}

static inline int AGSpectatorClearWait(void *canvas, uintptr_t token) {
    if (!token || AGSpectatorWaitToken(canvas) != token) return 0;
    uintptr_t *active = (uintptr_t *)((uint8_t *)canvas + 0x108);
    uintptr_t cached = *(uintptr_t *)((uint8_t *)canvas + 0xc8);
    return cached && __atomic_compare_exchange_n(active, &cached, 0, 0, __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE);
}
