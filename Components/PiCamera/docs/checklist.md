# F´ (F Prime) Component Development Checklist

**Component Name:** PiCamera  
**Component Owner:** _[Owner Name]_  
**Component Contributors:** _[Contributor Names]_  
**Review Date:** 2026-11-19  
**Checklist Version:** 1.2.0

_Pre-filled by fprime-auto-checklist 0.2.2 for `Components/PiCamera` at `b0be025b5a2c`. 🟢 YES 30, 🟠 NO 3, ⚪ N/A 3, 🔵 REVIEW 0, ⚫ UNCHECKED 37._
_Section fingerprints (inputs each section judges): 1=c4ab0b49f8fc 2=fe285759ea2d 3=7b69c40b1690 4=be838e6afb20 5=6e633d288c58_
_Stage: **implementation** (implementation and unit test); sections due: 1, 2, 3, 4_

## Status Legend

| Status | Meaning |
|--------|---------|
| 🟢 YES | Item satisfied -- verified by a tool (or attested by the checked record). |
| 🟠 NO | Not satisfied -- a tool found a violation; see Notes. |
| ⚪ N/A | Not applicable -- the model declares nothing this item concerns. |
| 🔵 REVIEW | Needs a human or LLM judgement; the rule to apply is in Notes. |
| ⚫ UNCHECKED | The deciding tool did not run (missing input, tool or license ack); see Notes. |

**Note:** Any status other than **🟢 YES** requires an explanation in the **Notes** column. A Status cell reads `<status> @<commit>`: decided by the tool at that commit; `by review` when a reviewer decided a row the tool left open; `overridden by reviewer` when a reviewer replaced the tool's verdict (reason in Notes).

## Definitions

| Term | Definition |
|------|------------|
| SDD | Software Description Document — the design documentation for the component. |
| Block diagram | A diagram illustrating the component's ports (and their directions/types), used to visualize the component's interfaces. |

_clang-tidy did not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin_

## 1. Requirements

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1.1 | Do requirements exist in the component SDD that define the component's expected operational behaviors? | 🟢 YES @b0be025b5a2c by review |  |
| 1.2 | Do requirements exist in the component SDD that define input data expected to be received and handled by the component? | 🟢 YES @b0be025b5a2c by review |  |
| 1.3 | Do requirements exist in the component SDD that define output data expected to be produced by the component? | 🟢 YES @b0be025b5a2c by review |  |
| 1.4 | Do requirements exist in the component SDD for all relevant memory usage constraints for the component? | 🟢 YES @b0be025b5a2c by review |  |
| 1.5 | Do requirements exist in the component SDD for all relevant hardware I/O usage constraints for the component? | 🟢 YES @b0be025b5a2c by review |  |
| 1.6 | Do requirements exist in the component SDD for all relevant runtime performance constraints for the component? | 🟢 YES @b0be025b5a2c by review |  |
| 1.7 | Does every requirement specify a verification method? | 🟢 YES @b0be025b5a2c | R8 pass (26 requirement(s) checked) |
| 1.8 | Are there any relevant external interface or functional requirements documented elsewhere such as ICDs/FDDs? If so, please specify in notes. | 🟢 YES @b0be025b5a2c | D9 pass (external references table: Other `libcamera-dev` 0.7.2, Raspberry Pi OS 13 (trixie) package installed on the target: libcamera public API; Other `libjpeg62-turbo-dev` 1:2.1.5-4, Debian 13 (trixie) main, as shipped by Raspberry Pi OS 13: libjpeg-turbo API; Standard JFIF 1.02; ITU-T T.81: JPEG File Interchange Format; Other `nasa/fprime` `devel@83221ba`, `Fw/Dp`, `Svc/DpManager`, `Svc/DpWriter`: F Prime data products; Other `nasa/fprime` `devel@83221ba`, `Svc/TlmChan` port `TlmGet`: F Prime telemetry store; Other `fprime-community/fprime-sensors@e5d83d1`, `Bmp280`, `MpuImu`, `NmeaGps` `Types.fpp`: Sensor reading types) |

## 2. Design

| # | Item | Status | Notes |
|---|------|--------|-------|
| 2.1 | Is the high level component functionality documented/described in the SDD? | 🟢 YES @b0be025b5a2c | SDD pass (tier platinum) |
| 2.2 | Is the component block diagram documented in the SDD and consistent with the FPP model? | 🟢 YES @b0be025b5a2c | D9 pass (external references table: Other `libcamera-dev` 0.7.2, Raspberry Pi OS 13 (trixie) package installed on the target: libcamera public API; Other `libjpeg62-turbo-dev` 1:2.1.5-4, Debian 13 (trixie) main, as shipped by Raspberry Pi OS 13: libjpeg-turbo API; Standard JFIF 1.02; ITU-T T.81: JPEG File Interchange Format; Other `nasa/fprime` `devel@83221ba`, `Fw/Dp`, `Svc/DpManager`, `Svc/DpWriter`: F Prime data products; Other `nasa/fprime` `devel@83221ba`, `Svc/TlmChan` port `TlmGet`: F Prime telemetry store; Other `fprime-community/fprime-sensors@e5d83d1`, `Bmp280`, `MpuImu`, `NmeaGps` `Types.fpp`: Sensor reading types) |
| 2.3 | Is the component port table documented in the SDD and consistent with the FPP model? | 🟢 YES @b0be025b5a2c | D7 pass (3 port(s) checked) |
| 2.4 | Are the component input port behaviors described in the SDD? | 🟢 YES @b0be025b5a2c | D10 pass (1 input port(s) checked) |
| 2.5 | Are the component input port handlers defined? | 🟢 YES @b0be025b5a2c | D1 pass (1 input port(s) checked) |
| 2.6 | Are the component command handlers defined? | 🟢 YES @b0be025b5a2c | D2 pass (1 command(s) checked) |
| 2.7 | Are the component sequence diagrams documented? | 🟢 YES @b0be025b5a2c | D9 pass (external references table: Other `libcamera-dev` 0.7.2, Raspberry Pi OS 13 (trixie) package installed on the target: libcamera public API; Other `libjpeg62-turbo-dev` 1:2.1.5-4, Debian 13 (trixie) main, as shipped by Raspberry Pi OS 13: libjpeg-turbo API; Standard JFIF 1.02; ITU-T T.81: JPEG File Interchange Format; Other `nasa/fprime` `devel@83221ba`, `Fw/Dp`, `Svc/DpManager`, `Svc/DpWriter`: F Prime data products; Other `nasa/fprime` `devel@83221ba`, `Svc/TlmChan` port `TlmGet`: F Prime telemetry store; Other `fprime-community/fprime-sensors@e5d83d1`, `Bmp280`, `MpuImu`, `NmeaGps` `Types.fpp`: Sensor reading types) |
| 2.8 | Are component state machines and use-cases described in the SDD? | 🟢 YES @b0be025b5a2c | D9 pass (external references table: Other `libcamera-dev` 0.7.2, Raspberry Pi OS 13 (trixie) package installed on the target: libcamera public API; Other `libjpeg62-turbo-dev` 1:2.1.5-4, Debian 13 (trixie) main, as shipped by Raspberry Pi OS 13: libjpeg-turbo API; Standard JFIF 1.02; ITU-T T.81: JPEG File Interchange Format; Other `nasa/fprime` `devel@83221ba`, `Fw/Dp`, `Svc/DpManager`, `Svc/DpWriter`: F Prime data products; Other `nasa/fprime` `devel@83221ba`, `Svc/TlmChan` port `TlmGet`: F Prime telemetry store; Other `fprime-community/fprime-sensors@e5d83d1`, `Bmp280`, `MpuImu`, `NmeaGps` `Types.fpp`: Sensor reading types) |
| 2.9 | Are the state machine actions defined? | ⚪ N/A @b0be025b5a2c | D3: no state machines declared |
| 2.10 | Are component commands, telemetry, events and parameters documented in the SDD (and consistent with the FPP model)? | 🟢 YES @b0be025b5a2c | D8 pass (11 dictionary item(s) checked) |
| 2.11 | Are component data products documented and consistent with the FPP model? | 🟢 YES @b0be025b5a2c | D8 pass (11 dictionary item(s) checked) |
| 2.12 | Are all data product containers assigned a default priority? | 🟢 YES @b0be025b5a2c | D4 pass (1 container(s) checked) |
| 2.13 | Does each component port in the FPP model have a known/planned use-case? | 🟢 YES @b0be025b5a2c | R6 pass (3 port(s) traced against 26 requirement(s); 3 covered by companion/SDD evidence)<br>D10 pass (1 input port(s) checked) |
| 2.14 | Are port directions and types as expected? | 🟢 YES @b0be025b5a2c | D7 pass (3 port(s) checked) |
| 2.15 | Is the component type as expected (passive, queued or active)? | 🟢 YES @b0be025b5a2c | D9 pass (external references table: Other `libcamera-dev` 0.7.2, Raspberry Pi OS 13 (trixie) package installed on the target: libcamera public API; Other `libjpeg62-turbo-dev` 1:2.1.5-4, Debian 13 (trixie) main, as shipped by Raspberry Pi OS 13: libjpeg-turbo API; Standard JFIF 1.02; ITU-T T.81: JPEG File Interchange Format; Other `nasa/fprime` `devel@83221ba`, `Fw/Dp`, `Svc/DpManager`, `Svc/DpWriter`: F Prime data products; Other `nasa/fprime` `devel@83221ba`, `Svc/TlmChan` port `TlmGet`: F Prime telemetry store; Other `fprime-community/fprime-sensors@e5d83d1`, `Bmp280`, `MpuImu`, `NmeaGps` `Types.fpp`: Sensor reading types) |
| 2.16 | Are all the component requirements mapped to design description and/or artifacts? | 🟢 YES @b0be025b5a2c | D5 pass (26 requirement(s) checked) |
| 2.17 | Does the component FPP compile and generate auto-code? | 🟢 YES @b0be025b5a2c | D6 pass (1 FPP file(s) checked) |

## 3. Implementation

| # | Item | Status | Notes |
|---|------|--------|-------|
| 3.1 | Are all component source dependencies listed in the CMakeLists.txt file for the component? | 🟢 YES @b0be025b5a2c | I1 pass (0 dependency module(s) checked) |
| 3.2 | Does the component compile without warnings for all required targets? | ⚫ UNCHECKED @b0be025b5a2c | I2 not run: not done yet: no build output to scan (the module was not built by this run) |
| 3.3 | Are all loops properly terminated/bounded? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/jpl-c/loop-bounds` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.4 | Has gating been provided for any potential cyclic error/status messages (e.g. log messages, events)? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/unthrottled-cyclic-event` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.5 | Do all switch statements have a break after each case and terminate with a default case? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/switch-default` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin<br>clang-tidy `cpp/fprime/switch-case-fallthrough` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.6 | Verify all non-empty case statements that fall through to the following case statement are explicitly commented as such | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/switch-case-fallthrough` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.7 | Are all variables locally defined unless global or specific visibility is required? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/global-mutable-variable` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.8 | Are all class members defined appropriately using private, public and protected keywords? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/public-data-member` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.9 | Verify that no floating point expressions are tested for equality/inequality | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/float-equality` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.10 | Is the precision of floating point numbers sufficient to ensure accuracy and floating-point equivalence is evaluated with margin (i.e. safe floating-point usage), and is not used in a loop control? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/float-narrowing` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin<br>clang-tidy `cpp/fprime/float-loop-control` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin<br>clang-tidy `cpp/fprime/float-equality` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.11 | Are all variables initialized before use? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/uninitialized-member` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin<br>clang-tidy `cpp/uninitialized-local` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.12 | Are the priorities of all data products produced by the component configurable via command(s) or parameter(s)? | 🟠 NO @b0be025b5a2c | I3: container 'Capture' priority is not configurable: no command or parameter mentioning 'priority' found |
| 3.13 | Are all commands acknowledged with success/failure? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/command-response` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.14 | Do all validation failure cases for port and command handlers include a return statement to avoid unintended code execution beyond validation failures? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/validation-failure-return` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.15 | Are all internal port interfaces invoked via the auto-coded internal port invoke() function? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/internal-port-invoke` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.16 | All pointer arguments to functions are checked to be not nullptr using FW_ASSERT | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/checking-parameter-values` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.17 | Assumptions on software state are validated using FW_ASSERT. | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/jpl-c/use-of-assertions-density` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.18 | Assertions shall not be used to validate state that could be dependent on hardware or user input. | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/assert-on-untrusted-input` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.19 | Verify all ISR code is free of floating point operations | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/no-float-in-isr` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.20 | Has the ISR code been optimized to minimize length/execution time? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/isr-complexity` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.21 | Verify any software state that's expected upon receive of an interrupt is configured prior to enabling/setting conditions that would allow the interrupt to trigger. | ⚪ N/A @b0be025b5a2c by review | The component registers no interrupt handler; frames arrive on a camera library thread |
| 3.22 | Verify there are no blocking operations in ISRs | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/no-blocking-in-isr` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.23 | Verify any relevant interrupt enables and interrupts are cleared during initialization and re-enabled selectively as needed. | ⚪ N/A @b0be025b5a2c by review | The component enables no interrupt |
| 3.24 | Are RateGroup schedule calls non-blocking? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/no-blocking-in-sched-handler` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.25 | Verify no synchronous file access is done within a critical region (e.g. SchedIn) | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/no-file-access-in-critical` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.26 | Verify that all loops and if/else statements are compound statements (i.e. always use brackets {}) | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/compound-statements` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.27 | Verify that all divisions first check for small numbers (including zero) | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/division-guard` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin<br>clang-tidy `cpp/fprime/float-division-guard` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.28 | Verify all array accesses are checked to be within array index bounds | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/unchecked-array-index` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin<br>clang-tidy `cpp/fprime/checking-parameter-values` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.29 | Verify there are no function declarations within a function. | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/no-function-decl-in-function` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.30 | Verify that the three expressions in all for statements only concern flow control | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/for-header-flow-control` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.31 | Verify that there are no dependencies on signed integer overflow behavior | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/signed-overflow` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.32 | Verify return values are used or voided otherwise. | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/jpl-c/checking-return-values` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.33 | Verify units are incorporated into variable name, where applicable | 🟠 NO @b0be025b5a2c by review | PiCamera.fpp CaptureMetrics members latitude, longitude, roll, pitch, temperature carry no unit in the name (units are in the annotations); the model is the approved SDD |
| 3.34 | Verify that all invariant numbers are in enums, static constexpr or #defines. Enums or static constexpr must be used unless #define is only way to specify constant. | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/magic-numbers` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin<br>clang-tidy `cpp/fprime/define-constant` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.35 | Verify no use of printf | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/no-printf` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.36 | Does the component use platform independent standard data types (e.g. I32, F32 etc.) rather than primitive data types (e.g. int, float etc.)? | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/jpl-c/basic-int-types` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 3.37 | Does the component pass static analysis? | ⚫ UNCHECKED @b0be025b5a2c | I4: check not run |
| 3.38 | Does the implementation address all component requirements and remains consistent with the documented design? | 🟢 YES @b0be025b5a2c by review |  |

## 4. Unit Testing

| # | Item | Status | Notes |
|---|------|--------|-------|
| 4.1 | Have all test output/results been published? | ⚫ UNCHECKED @b0be025b5a2c | U1 not run: not done yet: no published unit-test artifacts given (--artifacts-dir) |
| 4.2 | Are all component unit test source dependencies listed in the CMakeLists.txt file for the component? | 🟢 YES @b0be025b5a2c overridden by reviewer | U3: unit-test dependency 'TestUtils' (from #include "TestUtils/RuleBasedTesting.hpp") is not declared in the module's CMake files (add it to UT_DEPENDS/DEPENDS)<br>TestUtils is a header-only directory of the framework with no CMake module to name; Fw_Dp and STest are declared |
| 4.3 | Have input data ranges been tested for boundary conditions? | 🟢 YES @b0be025b5a2c by review |  |
| 4.4 | Do the unit tests pass a memory leak check? | ⚫ UNCHECKED @b0be025b5a2c | U4 not run: not done yet: the leak check (unit-test executable under LeakSanitizer/valgrind) has not been run |
| 4.5 | Is there sufficient code coverage? | 🟢 YES @b0be025b5a2c | U5 pass (line coverage 99.19% (threshold 80.00%)) |

## 5. Close-Out

| # | Item | Status | Notes |
|---|------|--------|-------|
| 5.1 | Verify no TBDs, TODOs or printfs in the code (no incomplete code). | ⚫ UNCHECKED @b0be025b5a2c | clang-tidy `cpp/fprime/incomplete-code` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin<br>clang-tidy `cpp/fprime/no-printf` not run: fprime clang-tidy plugin not found; build native/ (see native/CMakeLists.txt) or pass --tidy-plugin |
| 5.2 | Verify that component can be instantiated, connected, and compiled along with the Topology for all applicable targets. | ⚫ UNCHECKED @b0be025b5a2c | C1 not run: not done yet: no topology build performed by this run (pass --deployment with --build, or the process builds the deployment) |
| 5.3 | Verify that the flight deployment with component instantiation/connections runs successfully on a hardware platform. Indicate hardware platform used for checkout in Notes. | 🟠 NO @b0be025b5a2c | Human: Run the flight deployment that instantiates this component on the target hardware and record platform, deployment, commit, date, result and tester in docs/hardware-run.md (check C2 validates the record).<br>C2: no docs/hardware-run.md: record the hardware run (Platform, Deployment, Commit, Date, Result, Tester) |
| 5.4 | Update the SDD to accurately reflect the final state of the component. Add any additional design detail, including any known idiosyncrasies. | 🟢 YES @b0be025b5a2c | D7 pass (3 port(s) checked)<br>D8 pass (11 dictionary item(s) checked)<br>D9 pass (external references table: Other `libcamera-dev` 0.7.2, Raspberry Pi OS 13 (trixie) package installed on the target: libcamera public API; Other `libjpeg62-turbo-dev` 1:2.1.5-4, Debian 13 (trixie) main, as shipped by Raspberry Pi OS 13: libjpeg-turbo API; Standard JFIF 1.02; ITU-T T.81: JPEG File Interchange Format; Other `nasa/fprime` `devel@83221ba`, `Fw/Dp`, `Svc/DpManager`, `Svc/DpWriter`: F Prime data products; Other `nasa/fprime` `devel@83221ba`, `Svc/TlmChan` port `TlmGet`: F Prime telemetry store; Other `fprime-community/fprime-sensors@e5d83d1`, `Bmp280`, `MpuImu`, `NmeaGps` `Types.fpp`: Sensor reading types)<br>SDD pass (tier platinum) |
| 5.5 | Validate that CI passes. | ⚫ UNCHECKED @b0be025b5a2c | C3 not run: not done yet: CI status not consulted (needs the repository, the commit and GITHUB_TOKEN) |

## Hand-off

Nothing to review at the **implementation** stage.
