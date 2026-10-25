#!/usr/bin/env python3
"""Cliente EXCLUSIVO V2: M27C256B PRESTO II, Mega e fontes integradas."""
import argparse
from pathlib import Path
import struct
import time
import zlib

SIZE = 32768
MAGIC = b'E2'
IDENTITY = b'EPROM27 V2 M27C256B_PRESTOII AUTO_RAILS MAX128'
MAX_REPLY = 256


def exact(port, size):
    data = bytearray()
    while len(data) < size:
        part = port.read(size-len(data))
        if not part:
            raise RuntimeError('Timeout/desconexao; estado eletrico nao confirmado.')
        data.extend(part)
    return bytes(data)


def encode(command, sequence, payload=b''):
    if len(command) != 1 or not 0 <= sequence <= 65535 or len(payload) > 131:
        raise ValueError('Frame fora dos limites V2.')
    body = command + struct.pack('<HH', sequence, len(payload)) + payload
    return MAGIC + body + struct.pack('<I', zlib.crc32(body))


class Programmer:
    def __init__(self, port):
        self.port = port
        self.sequence = 0
        self.identified = False

    def request(self, command, payload=b''):
        sequence = self.sequence
        self.sequence = (sequence+1) & 0xFFFF
        frame = encode(command, sequence, payload)
        sent = self.port.write(frame)
        if sent != len(frame):
            raise RuntimeError('Envio incompleto; nao repetir bloco automaticamente.')
        if exact(self.port, 2) != MAGIC:
            raise RuntimeError('Envelope inesperado; pode ser firmware V1 ou reset.')
        header = exact(self.port, 5)
        cmd, reply_sequence, length = struct.unpack('<cHH', header)
        if cmd != command or reply_sequence != sequence:
            raise RuntimeError('Resposta fora da sequencia; nao repetir gravacao.')
        if not 1 <= length <= MAX_REPLY:
            raise RuntimeError('Comprimento de resposta invalido.')
        data = exact(self.port, length)
        crc = struct.unpack('<I', exact(self.port, 4))[0]
        if zlib.crc32(header+data) != crc:
            raise RuntimeError('CRC da resposta invalido.')
        if data[0]:
            raise RuntimeError('Firmware: '+data[1:].decode('ascii', errors='replace'))
        return data[1:]

    def identify(self):
        result = self.request(b'I')
        if result != IDENTITY:
            raise RuntimeError('Perfil inesperado: '+repr(result))
        self.identified = True
        return result.decode('ascii')

    def expect(self, command, text, payload=b''):
        if self.request(command, payload) != text:
            raise RuntimeError('Resposta inesperada para '+command.decode('ascii'))

    def disarm(self):
        # Nao afirmar estado seguro se a porta/reset/firmware nao confirmar D.
        try:
            self.expect(b'D', b'DISARMED')
            return True
        except Exception:
            return False

    def diagnostics(self):
        data = self.request(b'P')
        if len(data) != 18:
            raise RuntimeError('Resposta de tensoes invalida.')
        stage, mode, vcc, vpp, vin, b5, *raw = struct.unpack('<BB8H',data)
        print(f'Estado={stage} chave={"GRAVAR" if mode else "LER"} '
              f'VCC={vcc/1000:.3f} V VPP={vpp/1000:.3f} V '
              f'VIN={vin/1000:.3f} V 5B={b5/1000:.3f} V')
        print('ADC bruto VCC/VPP/VIN/5B:', *raw)
        return stage, mode, vcc, vpp, vin, b5

    def select_calibration(self, voltage):
        selection = {'5':0,'6.25':1,'6':2,'4.2':3}[voltage]
        print('SERVICO SEM EPROM. Retire o chip e selecione LER antes de executar.')
        print('VPP segue VCC; este servico nunca aplica12,75V ao soquete.')
        result = self.request(b'K',bytes((selection,)))
        if result not in (b'CALIBRATION',b'UNCALIBRATED'):
            raise RuntimeError('Resposta de calibracao inesperada.')
        print(f'Alvo VCC={voltage} V. '+result.decode('ascii'))

    def calibrate(self, voltage):
        self.select_calibration(voltage)
        while True:
            self.diagnostics()
            if input('Ajuste com multimetro; Enter mede novamente, FIM retorna a 5 V: ').strip().upper() == 'FIM':
                return

    def pulse(self, voltage):
        self.select_calibration(voltage)
        self.diagnostics()
        print('SEM EPROM: pulso unico /CE nominal100us; /OE HIGH e enderecos isolados.')
        self.expect(b'Q', b'PULSE_100US')
        print('Pulso unico emitido. Medir95..105us no pino20; nao e teste de gravacao.')

    def read_image(self):
        if not self.identified:
            raise RuntimeError('Handshake V2 obrigatorio.')
        data = bytearray()
        for address in range(0, SIZE, 128):
            block = self.request(b'R', struct.pack('<HH', address, 128))
            if len(block) != 128:
                raise RuntimeError('Bloco de leitura incompleto.')
            data.extend(block)
        return bytes(data)

    def stable_read(self):
        reference = None
        for number in range(1, 4):
            image = self.read_image()
            print(f'Leitura {number}: CRC32={zlib.crc32(image):08X} '
                  f'FF={image.count(255)} ZERO={image.count(0)}')
            if reference is not None and image != reference:
                bad = next(i for i in range(SIZE) if image[i] != reference[i])
                raise RuntimeError(f'Leituras divergentes em 0x{bad:04X}; nao salvar.')
            reference = image
        return reference

    def blocks(self, command, image):
        if len(image) != SIZE:
            raise ValueError('Imagem deve ter exatamente 32768 bytes.')
        for address in range(0, SIZE, 128):
            block = image[address:address+128]
            payload = struct.pack('<HB', address, len(block))+block
            self.expect(command, b'OK', payload)

    def program(self, image):
        if not self.identified:
            raise RuntimeError('Handshake V2 obrigatorio.')
        if len(image) != SIZE:
            raise ValueError('Imagem deve ter exatamente 32768 bytes.')
        print('Selecione GRAVAR na chave e mantenha ate concluir as verificacoes.')
        if input('Digite GRAVAR para iniciar: ') != 'GRAVAR':
            raise RuntimeError('Cancelado antes da programacao.')
        try:
            self.expect(b'A', b'ARMED')
            self.blocks(b'W', image)
            for command, reply, voltage in (
                    (b'H', b'VERIFY_6V', '6,00 V'),
                    (b'L', b'VERIFY_4V2', '4,20 V'),
                    (b'F', b'VERIFY_5V', '5,00 V')):
                self.expect(command, reply)
                self.blocks(b'V', image)
                print('Comparacao integral byte a byte aprovada em '+voltage)
            self.expect(b'C', b'SUCCESS')
        except BaseException:
            confirmed = self.disarm()
            print('Retorno a leitura confirmado.' if confirmed else
                  'Sem confirmacao do retorno: desligue a fonte; confira VCC/VPP.')
            raise
        print('SUCCESS: gravacao e verificacoes integrais em 6 V, 4,2 V e 5 V.')


def input_image(path):
    image = Path(path).read_bytes()
    if len(image) != SIZE:
        raise RuntimeError('BIN deve conter exatamente 32768 bytes; sem padding automatico.')
    return image


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--porta', required=True, help='/dev/ttyACM0 ou COM3')
    parser.add_argument('acao', choices=('info','tensoes','calibrar','pulso','autoteste','ler','vazio','verificar','gravar'))
    parser.add_argument('arquivo', nargs='?')
    parser.add_argument('--vcc', choices=('4.2','5','6','6.25'),help='alvo do servico sem EPROM; pulso usa5V por padrao')
    args = parser.parse_args(argv)
    if args.acao in ('ler','verificar','gravar') and not args.arquivo:
        parser.error('Esta acao exige arquivo.')
    if args.acao == 'calibrar' and args.vcc is None:
        parser.error('calibrar exige --vcc {4.2,5,6,6.25}. Retire a EPROM.')
    if args.vcc is not None and args.acao not in ('calibrar','pulso'):
        parser.error('--vcc e exclusivo dos servicos calibrar/pulso.')
    if args.acao == 'ler' and Path(args.arquivo).exists():
        parser.error('Arquivo ja existe; escolha outro nome.')
    image = input_image(args.arquivo) if args.acao in ('verificar','gravar') else None
    import serial  # instalado somente no computador que usara a porta real
    with serial.Serial(args.porta,115200,timeout=60,write_timeout=10) as port:
        time.sleep(3.0)  # DTR pode reiniciar o Mega; setup recupera VPP antes de VCC
        port.reset_input_buffer()
        device = Programmer(port)
        try:
            if args.acao == 'tensoes':
                device.diagnostics()
                return
            if args.acao == 'calibrar':
                device.calibrate(args.vcc)
                return
            if args.acao == 'pulso':
                device.pulse(args.vcc or '5')
                return
            print(device.identify())
            if args.acao == 'autoteste':
                if device.request(b'S') != bytes((0,255,170,85)):
                    raise RuntimeError('Autoteste MOSFET/comparador reprovado.')
                print('Autoteste 00/FF/AA/55 aprovado; nao testa chip nem pulsos.')
            elif args.acao in ('ler','vazio','verificar'):
                actual = device.stable_read()
                if args.acao == 'ler':
                    with open(args.arquivo,'xb') as out:
                        out.write(actual)
                    print('Salvos 32768 bytes em',args.arquivo)
                elif args.acao == 'vazio':
                    print('VAZIA: todos FF.' if actual == b'\xff'*SIZE else 'NAO VAZIA.')
                elif actual != image:
                    bad = next(i for i in range(SIZE) if actual[i] != image[i])
                    raise RuntimeError(f'Conteudo diferente em 0x{bad:04X}.')
                else:
                    print('BIN e EPROM identicos byte a byte.')
            elif args.acao == 'gravar':
                device.program(image)
        finally:
            if (device.identified or args.acao in ('calibrar','pulso')) and not device.disarm():
                print('Sem confirmacao de D. Confira fontes e controles antes de retirar o chip.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError,OSError,ValueError) as exc:
        raise SystemExit('ERRO: '+str(exc))
    except KeyboardInterrupt:
        raise SystemExit('Interrompido; confira VCC/VPP antes de retirar a EPROM.')
