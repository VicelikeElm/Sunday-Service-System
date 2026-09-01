from sss_diagnostics import (
    export_diagnostic_bundle,
    report_text,
    run_full_system_test,
)

report = run_full_system_test()

print()
print(report_text(report))

bundle = export_diagnostic_bundle(
    report
)

print("Diagnostic ZIP:")
print(bundle)
print()
print(
    "The test was read-only. It did not start/stop recording or streaming, "
    "move cameras/slides, or change audio mute state."
)
