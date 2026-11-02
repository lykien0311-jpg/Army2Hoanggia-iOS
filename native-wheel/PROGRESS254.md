# Build254: remove the B253 status overlay

The user confirms Build253 auto works and requests removal of theB253
measurement/status panel shown in35383.jpg. Exclude UfoDiagnostics.m from
the iPhone/device dylib build, removing its window, label, constructor, timer
and automatic file writer. Keep the simulator-only fixture.

All four UFO auto source/header files are byte-identical to the accepted253
sources. The native main is byte-identical; normal shots, conditional POW
and the no-inventory-item behavior retain that implementation.

Use isolated branch codex/army-ios-remove-b253 at8a4376b33254211eed46cd91fbf508af58f4e10d.
The concurrent auto-session rewrite on codex/army-ios-build is not included.
Apple workflow41296244636 / artifact13079491626 passes strict signing and
re-signing, existing simulator checks and device absence checks for the
diagnostic window class, B253 label and log filename.
The exact packaged dylib passes60 native encounter and12 completion/wait
cases. The final IPA changes only the dylib and bundle build;523 other
entries, including the main executable, match the user's working253 IPA.
New-build physical acceptance remains untested.
