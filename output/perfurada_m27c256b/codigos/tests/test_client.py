"""Testes novos do protocolo/cliente V2; nenhum acesso a porta real."""
import contextlib
import importlib.util
import io
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import zlib

SPEC = importlib.util.spec_from_file_location('eprom_pc', Path(__file__).parents[1]/'eprom_pc.py')
client = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(client)


def reply(command, sequence, body=b'OK', status=0):
    data = bytes((status,))+body
    header = struct.pack('<cHH', command, sequence, len(data))
    return b'E2'+header+data+struct.pack('<I', zlib.crc32(header+data))


class Port:
    def __init__(self, callback):
        self.callback = callback
        self.rx = bytearray()
        self.requests = []
        self.chunk = 65536

    def write(self, frame):
        if frame[:2] != b'E2':
            raise AssertionError('wrong magic')
        command, sequence, size = struct.unpack('<cHH',frame[2:7])
        if len(frame) != size+11:
            raise AssertionError('wrong frame size')
        if zlib.crc32(frame[2:-4]) != struct.unpack('<I',frame[-4:])[0]:
            raise AssertionError('wrong request CRC')
        payload = frame[7:-4]
        self.requests.append((command,sequence,payload))
        response = self.callback(command,sequence,payload)
        self.rx.extend(response)
        return len(frame)

    def read(self, count):
        count = min(count, self.chunk, len(self.rx))
        result = bytes(self.rx[:count])
        del self.rx[:count]
        return result


class ClientTest(unittest.TestCase):
    def test_encode_known_format_and_bounds(self):
        packet = client.encode(b'W',0x1234,b'\xff\x7f\x01\x55')
        self.assertEqual(packet[:7],b'E2W\x34\x12\x04\x00')
        self.assertEqual(zlib.crc32(packet[2:-4]),struct.unpack('<I',packet[-4:])[0])
        for cmd,seq,data in ((b'WW',0,b''),(b'W',-1,b''),(b'W',65536,b''),(b'W',0,b'0'*132)):
            with self.assertRaises(ValueError):
                client.encode(cmd,seq,data)

    def test_partial_reads_and_sequence_wrap(self):
        port = Port(lambda c,s,p:reply(c,s))
        port.chunk = 1
        device = client.Programmer(port)
        device.sequence = 65535
        self.assertEqual(device.request(b'D'),b'OK')
        device.request(b'D')
        self.assertEqual([r[1] for r in port.requests],[65535,0])

    def test_reject_old_identity(self):
        device = client.Programmer(Port(lambda c,s,p:reply(c,s,b'EPROM27 V1 PROGRAMMER')))
        with self.assertRaisesRegex(RuntimeError,'Perfil inesperado'):
            device.identify()
        self.assertFalse(device.identified)

    def test_invalid_reply_variants(self):
        variants = (
            lambda c,s: b'READY\r\n',
            lambda c,s: reply(b'X',s),
            lambda c,s: reply(c,(s+1)&65535),
            lambda c,s: b'E2'+struct.pack('<cHH',c,s,257),
            lambda c,s: b'E2'+struct.pack('<cHH',c,s,0),
            lambda c,s: reply(c,s)[:-1]+bytes((reply(c,s)[-1]^1,)),
            lambda c,s: reply(c,s,b'POWER',1),
            lambda c,s: b'E2',
        )
        for variant in variants:
            with self.subTest(variant=variant):
                device = client.Programmer(Port(lambda c,s,p:variant(c,s)))
                with self.assertRaises(RuntimeError):
                    device.request(b'I')

    def test_partial_write_no_retry(self):
        port = Port(lambda c,s,p:reply(c,s))
        device = client.Programmer(port)
        port.write = lambda _: 1
        with self.assertRaisesRegex(RuntimeError,'Envio incompleto'):
            device.request(b'W')

    def test_read_full_bounds_binary(self):
        image = bytes(range(256))*128
        def exchange(c,s,p):
            self.assertEqual(c,b'R')
            address,count = struct.unpack('<HH',p)
            self.assertEqual(count,128)
            self.assertLessEqual(address+count,32768)
            return reply(c,s,image[address:address+count])
        port = Port(exchange)
        device = client.Programmer(port)
        device.identified = True
        self.assertEqual(device.read_image(),image)
        self.assertEqual(len(port.requests),256)
        self.assertEqual(struct.unpack('<HH',port.requests[-1][2]),(32640,128))

    def test_unidentified_read_and_program_rejected(self):
        device = client.Programmer(Port(lambda c,s,p:reply(c,s)))
        with self.assertRaisesRegex(RuntimeError,'Handshake'):
            device.read_image()
        with self.assertRaisesRegex(RuntimeError,'Handshake'):
            device.program(b'\xff'*32768)

    def test_stable_reads_require_exact_comparison(self):
        device = client.Programmer(Port(lambda c,s,p:reply(c,s)))
        device.read_image = lambda: b'\xff'*32768
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(device.stable_read(),b'\xff'*32768)
        images = iter((b'\xff'*32768,b'\x00'+b'\xff'*32767))
        device.read_image = lambda:next(images)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError,'0x0000'):
            device.stable_read()

    def test_program_exact_four_passes_and_success_order(self):
        image = bytes(range(256))*128
        phase = 'init'
        next_address = 0
        completed = []
        def exchange(c,s,p):
            nonlocal phase,next_address
            if c == b'A':
                self.assertEqual(phase,'init')
                phase = 'write'
                return reply(c,s,b'ARMED')
            if c in (b'W',b'V'):
                self.assertEqual(c,b'W' if phase == 'write' else b'V')
                address,count = struct.unpack('<HB',p[:3])
                self.assertEqual(address,next_address)
                self.assertEqual(count,128)
                self.assertEqual(p[3:],image[address:address+count])
                next_address += count
                return reply(c,s)
            if c in (b'H',b'L',b'F'):
                self.assertEqual(next_address,32768)
                completed.append(phase)
                expected = {'write':(b'H','high',b'VERIFY_6V'),
                            'high':(b'L','low',b'VERIFY_4V2'),
                            'low':(b'F','final',b'VERIFY_5V')}[phase]
                self.assertEqual(c,expected[0])
                phase = expected[1]
                next_address = 0
                return reply(c,s,expected[2])
            if c == b'C':
                self.assertEqual((phase,next_address),('final',32768))
                completed.append(phase)
                return reply(c,s,b'SUCCESS')
            self.fail('unexpected command')
        device = client.Programmer(Port(exchange))
        device.identified = True
        with patch('builtins.input',return_value='GRAVAR'),contextlib.redirect_stdout(io.StringIO()):
            device.program(image)
        self.assertEqual(completed,['write','high','low','final'])

    def test_errors_at_every_phase_disarm_and_preserve_error(self):
        for failing in (b'A',b'W',b'H',b'L',b'F',b'C'):
            with self.subTest(failing=failing):
                def exchange(c,s,p):
                    if c == failing:
                        return reply(c,s,b'TEST_FAILURE',1)
                    return reply(c,s,{b'A':b'ARMED',b'H':b'VERIFY_6V',b'L':b'VERIFY_4V2',
                                      b'F':b'VERIFY_5V',b'D':b'DISARMED'}.get(c,b'OK'))
                port = Port(exchange)
                device = client.Programmer(port)
                device.identified = True
                with patch('builtins.input',return_value='GRAVAR'),contextlib.redirect_stdout(io.StringIO()),self.assertRaisesRegex(RuntimeError,'TEST_FAILURE'):
                    device.program(b'\xff'*32768)
                self.assertEqual(port.requests[-1][0],b'D')
                self.assertNotIn(b'C',[r[0] for r in port.requests] if failing != b'C' else [])

    def test_disarm_failure_does_not_mask_original(self):
        def exchange(c,s,p):
            return b'' if c == b'D' else reply(c,s,b'ORIGINAL',1)
        device = client.Programmer(Port(exchange))
        device.identified = True
        with patch('builtins.input',return_value='GRAVAR'),contextlib.redirect_stdout(io.StringIO()),self.assertRaisesRegex(RuntimeError,'ORIGINAL'):
            device.program(b'\xff'*32768)

    def test_interrupt_attempts_disarm(self):
        port = Port(lambda c,s,p:reply(c,s,b'DISARMED'))
        device = client.Programmer(port)
        device.identified = True
        original = device.request
        device.request = lambda c,p=b'': (_ for _ in ()).throw(KeyboardInterrupt()) if c == b'A' else original(c,p)
        with patch('builtins.input',return_value='GRAVAR'),contextlib.redirect_stdout(io.StringIO()),self.assertRaises(KeyboardInterrupt):
            device.program(b'\xff'*32768)
        self.assertEqual(port.requests[-1][0],b'D')

    def test_bad_image_rejected_before_transport(self):
        device = client.Programmer(Port(lambda c,s,p:reply(c,s)))
        for size in (0,32767,32769):
            with self.assertRaises(ValueError):
                device.blocks(b'W',b'\xff'*size)

    def test_calibration_maps_all_modes_without_handshake(self):
        for voltage,selection in (('5',0),('6.25',1),('6',2),('4.2',3)):
            port = Port(lambda c,s,p:reply(c,s,b'UNCALIBRATED'))
            device = client.Programmer(port)
            with contextlib.redirect_stdout(io.StringIO()):
                device.select_calibration(voltage)
            self.assertEqual(port.requests[0][0],b'K')
            self.assertEqual(port.requests[0][2],bytes((selection,)))
            self.assertFalse(device.identified)

    def test_calibration_holds_and_repeats_diagnostic_until_fim(self):
        def exchange(c,s,p):
            return reply(c,s,b'CALIBRATION' if c == b'K' else struct.pack('<BB8H',5,0,4200,4200,12000,5000,344,141,403,409))
        port = Port(exchange)
        device = client.Programmer(port)
        with patch('builtins.input',side_effect=('', 'FIM')),contextlib.redirect_stdout(io.StringIO()):
            device.calibrate('4.2')
        self.assertEqual([r[0] for r in port.requests],[b'K',b'P',b'P'])

    def test_service_pulse_is_single_after_diagnostics(self):
        def exchange(c,s,p):
            body = {b'K':b'CALIBRATION',b'P':struct.pack('<BB8H',5,0,6250,6250,12000,5000,512,210,403,409),b'Q':b'PULSE_100US'}[c]
            return reply(c,s,body)
        port = Port(exchange)
        with contextlib.redirect_stdout(io.StringIO()):
            client.Programmer(port).pulse('6.25')
        self.assertEqual([r[0] for r in port.requests],[b'K',b'P',b'Q'])

    def test_service_error_stops_before_pulse(self):
        port = Port(lambda c,s,p:reply(c,s,b'VPP_STUCK',1))
        with self.assertRaisesRegex(RuntimeError,'VPP_STUCK'):
            client.Programmer(port).pulse('5')
        self.assertEqual([r[0] for r in port.requests],[b'K'])


if __name__ == '__main__':
    unittest.main()
