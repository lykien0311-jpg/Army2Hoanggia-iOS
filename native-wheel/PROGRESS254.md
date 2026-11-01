# Build254: remove the B253 status overlay

The user confirms Build253 auto works and requests removal of theB253
measurement/status panel shown in35383.jpg.

Exclude UfoDiagnostics.m from the iPhone/device dylib build. This removes its
window, label, constructor, polling timer and automatic diagnostic file writer.
Keep the simulator-only diagnostic fixture for the existing validation flow.
Assert that the runtime diagnostic window class, B253 label prefix and log
filename do not appear in the device dylib.

Turn33.c, UfoAuto.c and their headers remain byte-identical to the working253
sources. The native main is preserved; normal shots, conditional POW and the
no-inventory-item behavior retain the implementation the user has tested.
