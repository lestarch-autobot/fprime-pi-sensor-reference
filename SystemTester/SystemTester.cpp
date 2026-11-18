// Test harness component: record markers and start reports
#include "SystemTester/SystemTester.hpp"

namespace SystemTester {

SystemTester::SystemTester(const char* const compName)
    : SystemTesterComponentBase(compName), m_uptimeS(0), m_started(false) {}

SystemTester::~SystemTester() {}

void SystemTester::run_handler(FwIndexType portNum, U32 context) {
    if (not this->m_started) {
        this->m_started = true;
        this->log_ACTIVITY_HI_Started();
    }
    this->tlmWrite_UptimeS(this->m_uptimeS);
    this->m_uptimeS++;
}

void SystemTester::MARK_cmdHandler(FwOpcodeType opCode, U32 cmdSeq, U32 id) {
    this->log_ACTIVITY_HI_Marker(id);
    this->cmdResponse_out(opCode, cmdSeq, Fw::CmdResponse::OK);
}

}  // namespace SystemTester
