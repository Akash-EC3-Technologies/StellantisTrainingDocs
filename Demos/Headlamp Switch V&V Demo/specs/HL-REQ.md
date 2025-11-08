# **Software Requirements Specification (SRS)**

**Item:** Headlamp Switch Control
**Document ID:** HL-REQ
**Version:** 1.0
**Safety Integrity Level (ASIL):** QM *(none)*
**Scope:** Control of headlamp output via discrete switch. The software debounces the input and ensures deterministic timing behavior.

## 1. Interface Signals

| Signal      | Description             | Type    | Direction | Electrical/Logical Details          |
| :---------- | :---------------------- | :------ | :-------- | :---------------------------------- |
| `SWITCH_IN` | Headlamp switch input   | Digital | Input     | GPIO 27, pull-up, pressed = logic 0 |
| `LAMP_OUT`  | Headlamp output control | Digital | Output    | GPIO 17, active-high (1 = lamp ON)  |

## 2. Software Functional Requirements

| **Req ID**     | **Title**               | **Type**                    | **Description (shall-statement)**                                                                                                                             | **Rationale / Notes**                                         | **Verification Method**       | **Acceptance Criteria**                                             | **Traceability**                |
| :------------- | :---------------------- | :-------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------ | :---------------------------- | :------------------------------------------------------------------ | :------------------------------ |
| **HL-REQ-001** | Switch Press Response   | Functional                  | When `SWITCH_IN` transitions to **pressed** (logic 0) and remains stable ≥ 5 ms, the software **shall** set `LAMP_OUT` = 1 within **30 ms**.                  | Ensures prompt user feedback when headlamp switch is pressed. | Test (timing analysis)        | `LAMP_OUT`=1 observed ≤ 30 ms after debounced press.                | System Req → HL-SYS-001         |
| **HL-REQ-002** | Switch Release Response | Functional                  | When `SWITCH_IN` transitions to **released** (logic 1) and remains stable ≥ 5 ms, the software **shall** set `LAMP_OUT` = 0 within **30 ms**.                 | Maintains expected toggle behavior.                           | Test (timing analysis)        | `LAMP_OUT`=0 observed ≤ 30 ms after debounced release.              | System Req → HL-SYS-001         |
| **HL-REQ-003** | Input Debounce          | Robustness                  | Pulses on `SWITCH_IN` shorter than **5 ms** **shall not** affect `LAMP_OUT`.                                                                                  | Prevents false triggers from mechanical bounce.               | Test (signal injection)       | No change in `LAMP_OUT` for pulses < 5 ms.                          | Design → Debounce Filter Module |
| **HL-REQ-004** | Power-On Default State  | Initialization              | After application startup, `LAMP_OUT` **shall be OFF (0)** within **100 ms**.                                                                                 | Ensures defined and safe initial lamp state.                  | Test (startup observation)    | `LAMP_OUT`=0 ≤ 100 ms after power-on.                               | System Req → HL-SYS-002         |
| **HL-REQ-005** | Execution Cadence       | Performance / Liveness      | During normal operation, the application **shall process input and update output at least every 100 ms**.                                                     | Guarantees deterministic loop timing and responsiveness.      | Analysis + Test (task period) | Measured cycle time ≤ 100 ms.                                       | Architecture → Main Loop        |
| **HL-REQ-006** | Stuck Input Robustness  | Robustness / Fault Handling | If `SWITCH_IN` remains constant for **> 10 s**, the application **shall continue to operate without crash/hang** and maintain consistent `LAMP_OUT` behavior. | Ensures stability under constant input conditions.            | Test (long-duration run)      | No task watchdog reset or software hang during 10 s constant input. | Safety Analysis → Robustness    |
