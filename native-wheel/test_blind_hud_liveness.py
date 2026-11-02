"""All native HUD branches must have initialized stack locals after world skip."""
from pathlib import Path
from collections import deque
import json
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from capstone.arm64 import ARM64_OP_MEM,ARM64_OP_IMM,ARM64_REG_X29,ARM64_REG_SP
R=Path(__file__).resolve().parent
b=(R.parent/'validation/inspect-ipa/Army2Hoanggia').read_bytes()
maps=json.loads((R/'blind-map.json').read_text());md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.detail=True
checks=0
for m in maps:
    start,end,hud=m['paint'],m['paint']+0x23fc,m['hud']
    instructions={i.address:i for i in md.disasm(b[start:end],start)}
    # Original prologue arguments/saved registers plus all seven values in
    # the world-skip hook. SP is FP-0x140 through the native painter body.
    init=set(range(-0x68,16))
    for o in (-0x6c,-0x8c,-0x90,-0x94,-0x80,-0x88,-0xd4):init.update(range(o,o+4))
    init.update((10019,10022))
    seen={hud:init};todo=deque([hud]);undefined={};undefined_registers={}
    def width(i):
        if i.mnemonic.endswith(('rb','rsb')):return 1
        if i.mnemonic.endswith(('rh','rsh')):return 2
        if i.mnemonic.endswith('rsw'):return 4
        name=i.reg_name(i.operands[0].reg)
        return 8 if name.startswith(('x','d')) else 16 if name.startswith('q') else 4
    while todo:
        a=todo.popleft();i=instructions[a];defined=seen[a].copy()
        if i.mnemonic=='sub' and i.op_str.startswith('sp, x29'):continue
        def callee(reg):
            name=md.reg_name(reg)
            return 10000+int(name[1:]) if name.startswith(('w','x')) and name[1:].isdigit() and 19<=int(name[1:])<=28 else None
        read,write=i.regs_access()
        required={callee(reg) for reg in read}-{None}
        if required-defined:undefined_registers[a]=(i.mnemonic,i.op_str,sorted(required-defined))
        defined.update({callee(reg) for reg in write}-{None})
        for op in i.operands:
            if op.type!=ARM64_OP_MEM or op.mem.base not in (ARM64_REG_SP,ARM64_REG_X29):continue
            n=width(i)*(2 if i.mnemonic in ('stp','ldp') else 1)
            offset=op.mem.disp+(-0x140 if op.mem.base==ARM64_REG_SP else 0);slots=set(range(offset,offset+n))
            if i.mnemonic.startswith('ld'):
                if slots-defined:undefined[a]=(i.mnemonic,i.op_str,sorted(slots-defined))
            elif i.mnemonic.startswith('st'):defined.update(slots)
        targets=[o.imm for o in i.operands if o.type==ARM64_OP_IMM]
        if i.mnemonic=='b':nexts=targets[-1:]
        elif i.mnemonic.startswith('b.') or i.mnemonic in ('cbz','cbnz','tbz','tbnz'):nexts=[a+4]+targets[-1:]
        elif i.mnemonic in ('ret','br'):nexts=[]
        else:nexts=[a+4]
        for n in nexts:
            if n not in instructions:continue
            merged=defined if n not in seen else defined&seen[n]
            if n not in seen or merged!=seen[n]:seen[n]=merged;todo.append(n)
    assert not undefined,(m['variant'],undefined)
    assert not undefined_registers,(m['variant'],undefined_registers)
    checks+=len(seen)
report=dict(passed=True,variants=6,reachable_native_HUD_instructions=checks,
    undefined_stack_reads=0,undefined_incoming_callee_saved_registers=0,all_conditional_HUD_branches_checked=True)
(R/'build/blind-hud-liveness-check.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',report)
