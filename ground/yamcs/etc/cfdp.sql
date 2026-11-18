create stream cfdp_in as select substring(packet, 8) as pdu from tm_realtime where extract_short(packet, 0) = 3
create stream cfdp_out (gentime TIMESTAMP, entityId long, seqNum int, pdu binary)
insert into tc_realtime select gentime, 'cfdp-service' as origin, seqNum, '/yamcs/cfdp/upload' as cmdName, unhex('1003C00000000003') + pdu as binary from cfdp_out
