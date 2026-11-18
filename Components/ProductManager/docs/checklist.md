# F´ (F Prime) Component Development Checklist

**Component Name:** ProductManager  
**Component Owner:** _[Owner Name]_  
**Component Contributors:** _[Contributor Names]_  
**Review Date:** 2026-11-18  
**Checklist Version:** 1.2.0

_Pre-filled by fprime-auto-checklist 0.2.2 for `Components/ProductManager` at `2387c97c67b1`. 🟢 YES 23, 🟠 NO 4, ⚪ N/A 4, 🔵 REVIEW 5, ⚫ UNCHECKED 37._
_Section fingerprints (inputs each section judges): 1=2511e1f1699c 2=f758948a11dd 3=e3b0c44298fc 4=e3b0c44298fc 5=f758948a11dd_
_Stage: **design** (design (SDD + FPP model)); sections due: 1, 2_

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

_clang-tidy did not run: no translation units of /home/ubuntu/campaign/uut/Components/ProductManager in /home/ubuntu/campaign/uut/build-fprime-automatic-native/compile_commands.json; build the module first_

## 1. Requirements

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1.1 | Do requirements exist in the component SDD that define the component's expected operational behaviors? | 🟢 YES @2387c97c67b1 by review |  |
| 1.2 | Do requirements exist in the component SDD that define input data expected to be received and handled by the component? | 🟢 YES @2387c97c67b1 by review |  |
| 1.3 | Do requirements exist in the component SDD that define output data expected to be produced by the component? | 🟢 YES @2387c97c67b1 by review |  |
| 1.4 | Do requirements exist in the component SDD for all relevant memory usage constraints for the component? | 🟢 YES @2387c97c67b1 by review |  |
| 1.5 | Do requirements exist in the component SDD for all relevant hardware I/O usage constraints for the component? | ⚪ N/A @2387c97c67b1 by review | No hardware I/O: camera, sensors and radio are reached through ports, files through the OS (SDD 7, hardware row). |
| 1.6 | Do requirements exist in the component SDD for all relevant runtime performance constraints for the component? | 🟢 YES @2387c97c67b1 by review |  |
| 1.7 | Does every requirement specify a verification method? | 🟢 YES @2387c97c67b1 | R8 pass (49 requirement(s) checked) |
| 1.8 | Are there any relevant external interface or functional requirements documented elsewhere such as ICDs/FDDs? If so, please specify in notes. | 🟢 YES @2387c97c67b1 | D9 pass (external references table: System design `docs/ssdd.md` at `0f3a6b1`: PiSensor SSDD; Format nasa/fprime v4.4.2, `Fw/Dp/docs/sdd.md`: F Prime data product file format; Format nasa/fprime v4.4.2, `DP_FILENAME_FORMAT` of `config/DpCfg.hpp`: F Prime data product file name; Standard DP10, External Release V4, rule 4.4.6.4: JPL Design Principles) |

## 2. Design

| # | Item | Status | Notes |
|---|------|--------|-------|
| 2.1 | Is the high level component functionality documented/described in the SDD? | 🟢 YES @2387c97c67b1 | SDD pass (tier gold) |
| 2.2 | Is the component block diagram documented in the SDD and consistent with the FPP model? | 🟢 YES @2387c97c67b1 | D9 pass (external references table: System design `docs/ssdd.md` at `0f3a6b1`: PiSensor SSDD; Format nasa/fprime v4.4.2, `Fw/Dp/docs/sdd.md`: F Prime data product file format; Format nasa/fprime v4.4.2, `DP_FILENAME_FORMAT` of `config/DpCfg.hpp`: F Prime data product file name; Standard DP10, External Release V4, rule 4.4.6.4: JPL Design Principles) |
| 2.3 | Is the component port table documented in the SDD and consistent with the FPP model? | 🟢 YES @2387c97c67b1 | D7 pass (7 port(s) checked) |
| 2.4 | Are the component input port behaviors described in the SDD? | 🟢 YES @2387c97c67b1 | D10 pass (3 input port(s) checked) |
| 2.5 | Are the component input port handlers defined? | 🟠 NO @2387c97c67b1 | D1: input port 'imageIn' (async) has no 'imageIn_handler' override in the implementation<br>D1: input port 'fileDoneIn' (async) has no 'fileDoneIn_handler' override in the implementation<br>D1: input port 'run' (async) has no 'run_handler' override in the implementation |
| 2.6 | Are the component command handlers defined? | 🟠 NO @2387c97c67b1 | D2: command 'CAPTURE' has no 'CAPTURE_cmdHandler' in the implementation<br>D2: command 'DOWNLINK' has no 'DOWNLINK_cmdHandler' in the implementation<br>D2: command 'DELETE' has no 'DELETE_cmdHandler' in the implementation<br>D2: command 'LIST_PRODUCTS' has no 'LIST_PRODUCTS_cmdHandler' in the implementation |
| 2.7 | Are the component sequence diagrams documented? | 🟢 YES @2387c97c67b1 | D9 pass (external references table: System design `docs/ssdd.md` at `0f3a6b1`: PiSensor SSDD; Format nasa/fprime v4.4.2, `Fw/Dp/docs/sdd.md`: F Prime data product file format; Format nasa/fprime v4.4.2, `DP_FILENAME_FORMAT` of `config/DpCfg.hpp`: F Prime data product file name; Standard DP10, External Release V4, rule 4.4.6.4: JPL Design Principles) |
| 2.8 | Are component state machines and use-cases described in the SDD? | 🟢 YES @2387c97c67b1 | D9 pass (external references table: System design `docs/ssdd.md` at `0f3a6b1`: PiSensor SSDD; Format nasa/fprime v4.4.2, `Fw/Dp/docs/sdd.md`: F Prime data product file format; Format nasa/fprime v4.4.2, `DP_FILENAME_FORMAT` of `config/DpCfg.hpp`: F Prime data product file name; Standard DP10, External Release V4, rule 4.4.6.4: JPL Design Principles) |
| 2.9 | Are the state machine actions defined? | ⚪ N/A @2387c97c67b1 | D3: no state machines declared |
| 2.10 | Are component commands, telemetry, events and parameters documented in the SDD (and consistent with the FPP model)? | 🟢 YES @2387c97c67b1 | D8 pass (28 dictionary item(s) checked) |
| 2.11 | Are component data products documented and consistent with the FPP model? | 🟢 YES @2387c97c67b1 | D8 pass (28 dictionary item(s) checked) |
| 2.12 | Are all data product containers assigned a default priority? | 🟢 YES @2387c97c67b1 | D4 pass (1 container(s) checked) |
| 2.13 | Does each component port in the FPP model have a known/planned use-case? | 🟢 YES @2387c97c67b1 | R6 pass (7 port(s) traced against 49 requirement(s); 7 covered by companion/SDD evidence)<br>D10 pass (3 input port(s) checked) |
| 2.14 | Are port directions and types as expected? | 🟢 YES @2387c97c67b1 | D7 pass (7 port(s) checked) |
| 2.15 | Is the component type as expected (passive, queued or active)? | 🟢 YES @2387c97c67b1 | D9 pass (external references table: System design `docs/ssdd.md` at `0f3a6b1`: PiSensor SSDD; Format nasa/fprime v4.4.2, `Fw/Dp/docs/sdd.md`: F Prime data product file format; Format nasa/fprime v4.4.2, `DP_FILENAME_FORMAT` of `config/DpCfg.hpp`: F Prime data product file name; Standard DP10, External Release V4, rule 4.4.6.4: JPL Design Principles) |
| 2.16 | Are all the component requirements mapped to design description and/or artifacts? | 🟢 YES @2387c97c67b1 | D5 pass (49 requirement(s) checked) |
| 2.17 | Does the component FPP compile and generate auto-code? | 🟢 YES @2387c97c67b1 | D6 pass (1 FPP file(s) checked) |

## 3. Implementation

| # | Item | Status | Notes |
|---|------|--------|-------|
| 3.1 | Are all component source dependencies listed in the CMakeLists.txt file for the component? | ⚪ N/A @2387c97c67b1 | I1: no C++ sources found |
| 3.2 | Does the component compile without warnings for all required targets? | 🟢 YES @2387c97c67b1 | I2 pass (1 log(s) scanned) |
| 3.3 | Are all loops properly terminated/bounded? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/jpl-c/loop-bounds` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.4 | Has gating been provided for any potential cyclic error/status messages (e.g. log messages, events)? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/unthrottled-cyclic-event` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.5 | Do all switch statements have a break after each case and terminate with a default case? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/switch-default` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first<br>clang-tidy `cpp/fprime/switch-case-fallthrough` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.6 | Verify all non-empty case statements that fall through to the following case statement are explicitly commented as such | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/switch-case-fallthrough` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.7 | Are all variables locally defined unless global or specific visibility is required? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/global-mutable-variable` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.8 | Are all class members defined appropriately using private, public and protected keywords? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/public-data-member` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.9 | Verify that no floating point expressions are tested for equality/inequality | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/float-equality` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.10 | Is the precision of floating point numbers sufficient to ensure accuracy and floating-point equivalence is evaluated with margin (i.e. safe floating-point usage), and is not used in a loop control? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/float-narrowing` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first<br>clang-tidy `cpp/fprime/float-loop-control` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first<br>clang-tidy `cpp/fprime/float-equality` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.11 | Are all variables initialized before use? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/uninitialized-member` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first<br>clang-tidy `cpp/uninitialized-local` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.12 | Are the priorities of all data products produced by the component configurable via command(s) or parameter(s)? | 🟠 NO @2387c97c67b1 | I3: container 'Capture' priority is not configurable: no command or parameter mentioning 'priority' found |
| 3.13 | Are all commands acknowledged with success/failure? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/command-response` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.14 | Do all validation failure cases for port and command handlers include a return statement to avoid unintended code execution beyond validation failures? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/validation-failure-return` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.15 | Are all internal port interfaces invoked via the auto-coded internal port invoke() function? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/internal-port-invoke` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.16 | All pointer arguments to functions are checked to be not nullptr using FW_ASSERT | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/checking-parameter-values` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.17 | Assumptions on software state are validated using FW_ASSERT. | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/jpl-c/use-of-assertions-density` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.18 | Assertions shall not be used to validate state that could be dependent on hardware or user input. | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/assert-on-untrusted-input` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.19 | Verify all ISR code is free of floating point operations | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/no-float-in-isr` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.20 | Has the ISR code been optimized to minimize length/execution time? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/isr-complexity` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.21 | Verify any software state that's expected upon receive of an interrupt is configured prior to enabling/setting conditions that would allow the interrupt to trigger. | 🔵 REVIEW @2387c97c67b1 | CL-1: ISR state before enable (3.21): for every ISR-named function (*_isr, *interrupt_handler*, *_irq*) find the code that enables its interrupt; every variable the ISR reads or writes must be assigned on a path that completes before that enable call. |
| 3.22 | Verify there are no blocking operations in ISRs | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/no-blocking-in-isr` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.23 | Verify any relevant interrupt enables and interrupts are cleared during initialization and re-enabled selectively as needed. | 🔵 REVIEW @2387c97c67b1 | CL-2: Interrupt enables cleared at init (3.23): in the constructor/init/configure/preamble, interrupt-enable bits must be explicitly cleared or masked before peripheral configuration, not assumed clear from reset. |
| 3.24 | Are RateGroup schedule calls non-blocking? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/no-blocking-in-sched-handler` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.25 | Verify no synchronous file access is done within a critical region (e.g. SchedIn) | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/no-file-access-in-critical` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.26 | Verify that all loops and if/else statements are compound statements (i.e. always use brackets {}) | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/compound-statements` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.27 | Verify that all divisions first check for small numbers (including zero) | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/division-guard` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first<br>clang-tidy `cpp/fprime/float-division-guard` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.28 | Verify all array accesses are checked to be within array index bounds | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/unchecked-array-index` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first<br>clang-tidy `cpp/fprime/checking-parameter-values` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.29 | Verify there are no function declarations within a function. | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/no-function-decl-in-function` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.30 | Verify that the three expressions in all for statements only concern flow control | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/for-header-flow-control` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.31 | Verify that there are no dependencies on signed integer overflow behavior | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/signed-overflow` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.32 | Verify return values are used or voided otherwise. | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/jpl-c/checking-return-values` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.33 | Verify units are incorporated into variable name, where applicable | 🔵 REVIEW @2387c97c67b1 | CL-3: Units in names (3.33): every variable, member, parameter, telemetry channel and command argument carrying a physical quantity must encode its unit in the name (timeoutMs, angleRad, sizeBytes) or in an FPP annotation. |
| 3.34 | Verify that all invariant numbers are in enums, static constexpr or #defines. Enums or static constexpr must be used unless #define is only way to specify constant. | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/magic-numbers` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first<br>clang-tidy `cpp/fprime/define-constant` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.35 | Verify no use of printf | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/no-printf` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.36 | Does the component use platform independent standard data types (e.g. I32, F32 etc.) rather than primitive data types (e.g. int, float etc.)? | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/jpl-c/basic-int-types` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 3.37 | Does the component pass static analysis? | ⚫ UNCHECKED @2387c97c67b1 | I4: check not run |
| 3.38 | Does the implementation address all component requirements and remains consistent with the documented design? | 🔵 REVIEW @2387c97c67b1 | CL-4: Implementation matches requirements and design (3.38): for each requirement row locate the handler(s) that satisfy it and confirm the behaviour including each error path the SDD describes; report requirements with no implementing code and handler behaviour the SDD does not describe. |

## 4. Unit Testing

| # | Item | Status | Notes |
|---|------|--------|-------|
| 4.1 | Have all test output/results been published? | ⚫ UNCHECKED @2387c97c67b1 | U1 not run: not done yet: no published unit-test artifacts given (--artifacts-dir) |
| 4.2 | Are all component unit test source dependencies listed in the CMakeLists.txt file for the component? | ⚪ N/A @2387c97c67b1 | U3: no unit-test sources found |
| 4.3 | Have input data ranges been tested for boundary conditions? | 🔵 REVIEW @2387c97c67b1 | CL-5: Boundary tests (4.3): for each bounded quantity (array sizes, FW_ASSERT limits, configuration constants, command-argument ranges, queue depths) a unit test must exercise the limit value and one past it. |
| 4.4 | Do the unit tests pass a memory leak check? | ⚫ UNCHECKED @2387c97c67b1 | U4 not run: not done yet: the leak check (unit-test executable under LeakSanitizer/valgrind) has not been run |
| 4.5 | Is there sufficient code coverage? | ⚫ UNCHECKED @2387c97c67b1 | U5 not run: not done yet: no coverage/summary.txt; 'fprime-util check --coverage' has not been run for the module |

## 5. Close-Out

| # | Item | Status | Notes |
|---|------|--------|-------|
| 5.1 | Verify no TBDs, TODOs or printfs in the code (no incomplete code). | ⚫ UNCHECKED @2387c97c67b1 | clang-tidy `cpp/fprime/incomplete-code` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first<br>clang-tidy `cpp/fprime/no-printf` not run: no translation units of Components/ProductManager in build-fprime-automatic-native/compile_commands.json; build the module first |
| 5.2 | Verify that component can be instantiated, connected, and compiled along with the Topology for all applicable targets. | ⚫ UNCHECKED @2387c97c67b1 | C1 not run: not done yet: no topology build performed by this run (pass --deployment with --build, or the process builds the deployment) |
| 5.3 | Verify that the flight deployment with component instantiation/connections runs successfully on a hardware platform. Indicate hardware platform used for checkout in Notes. | 🟠 NO @2387c97c67b1 | Human: Run the flight deployment that instantiates this component on the target hardware and record platform, deployment, commit, date, result and tester in docs/hardware-run.md (check C2 validates the record).<br>C2: no docs/hardware-run.md: record the hardware run (Platform, Deployment, Commit, Date, Result, Tester) |
| 5.4 | Update the SDD to accurately reflect the final state of the component. Add any additional design detail, including any known idiosyncrasies. | 🟢 YES @2387c97c67b1 | D7 pass (7 port(s) checked)<br>D8 pass (28 dictionary item(s) checked)<br>D9 pass (external references table: System design `docs/ssdd.md` at `0f3a6b1`: PiSensor SSDD; Format nasa/fprime v4.4.2, `Fw/Dp/docs/sdd.md`: F Prime data product file format; Format nasa/fprime v4.4.2, `DP_FILENAME_FORMAT` of `config/DpCfg.hpp`: F Prime data product file name; Standard DP10, External Release V4, rule 4.4.6.4: JPL Design Principles)<br>SDD pass (tier gold) |
| 5.5 | Validate that CI passes. | ⚫ UNCHECKED @2387c97c67b1 | C3 not run: not done yet: CI status not consulted (needs the repository, the commit and GITHUB_TOKEN) |

## Hand-off

Nothing to review at the **design** stage.

Deferred to a later stage: 3.21, 3.23, 3.33, 3.38, 4.3.
