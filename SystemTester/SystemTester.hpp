// Test harness component: record markers and start reports
#ifndef SystemTester_SystemTester_HPP
#define SystemTester_SystemTester_HPP

#include "SystemTester/SystemTesterComponentAc.hpp"

namespace SystemTester {

class SystemTester final : public SystemTesterComponentBase {
  public:
    explicit SystemTester(const char* const compName);
    ~SystemTester();

  private:
    void run_handler(FwIndexType portNum, U32 context) override;
    void MARK_cmdHandler(FwOpcodeType opCode, U32 cmdSeq, U32 id) override;

    U32 m_uptimeS;   //!< Cycles of the 1 Hz rate group since start
    bool m_started;  //!< Started event already sent
};

}  // namespace SystemTester

#endif
