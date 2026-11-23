module PiSensor {

  @ TCP variant: Svc.Com adapter between the retry component and the TCP driver
  instance comStub: Svc.ComStub base id 0x10009000

  @ TCP variant: connects to the ground at the address and port given on the command line (-a, -p)
  instance comDriver: Drv.TcpClient base id 0x1000A000

}
