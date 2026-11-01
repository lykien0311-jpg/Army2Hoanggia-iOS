// ARM64 bridge for RoboVM 2.3.26's catch-all TrycatchContext.
// int AGWheelGuard(env, callback, context, rvmTrycatchEnter)
.text
.p2align 2
.globl _AGWheelGuard
.private_extern _AGWheelGuard
_AGWheelGuard:
    stp x20, x19, [sp, #-48]!
    stp x22, x21, [sp, #16]
    stp x29, x30, [sp, #32]
    add x29, sp, #32
    sub sp, sp, #208
    mov x19, x0
    mov x20, x1
    mov x21, x2
    ldr x8, [x19, #48]
    str x8, [sp, #192]
    str xzr, [sp, #8]
    mov w8, #-1
    str w8, [sp, #8]
    mov x1, sp
    blr x3
    cbnz w0, Lfailed
    mov x0, x19
    mov x1, x21
    blr x20
    mov w22, w0
    b Lleave
Lfailed:
    str xzr, [x19, #16]
    mov w22, #-1
Lleave:
    ldr x8, [sp]
    str x8, [x19, #56]
    ldr x8, [sp, #192]
    str x8, [x19, #48]
    mov w0, w22
    add sp, sp, #208
    ldp x29, x30, [sp, #32]
    ldp x22, x21, [sp, #16]
    ldp x20, x19, [sp], #48
    ret
