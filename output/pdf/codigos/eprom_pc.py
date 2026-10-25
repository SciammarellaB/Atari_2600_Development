#!/usr/bin/env python3
"""Cliente USB para eprom27.ino. Requer pyserial; nenhum pacote de ROMs."""
import argparse
from pathlib import Path
import struct
import time
import zlib
import serial

SIZE = 32768

def exact(s, n):
    data = bytearray()
    while len(data) < n:
        part = s.read(n - len(data))
        if not part:
            raise RuntimeError('Timeout: cabo, firmware ou alimentacao.')
        data.extend(part)
    return bytes(data)

def line(s):
    value = s.readline()
    if not value.endswith(b'\n'):
        raise RuntimeError('Resposta incompleta ou timeout.')
    text = value.decode('ascii', errors='replace').strip()
    if text.startswith('ERR'):
        raise RuntimeError(text)
    return text

def identify(s):
    time.sleep(2.5)  # abrir a serial costuma reiniciar o Mega
    s.reset_input_buffer()
    s.write(b'I')
    result = line(s)
    if not result.startswith('EPROM27 V1 '):
        raise RuntimeError('Firmware inesperado: ' + result)
    print(result)
    return result

def read_image(s):
    s.write(b'R')
    if line(s) != 'DATA 32768':
        raise RuntimeError('Cabecalho de leitura inesperado.')
    data = exact(s, SIZE)
    if exact(s, 2) != b'\r\n' or line(s) != 'END':
        raise RuntimeError('Final de leitura inesperado.')
    return data

def stable_read(s):
    images = []
    for n in range(3):
        image = read_image(s)
        print(f'Leitura {n+1}: CRC32={zlib.crc32(image):08X} '
              f'FF={image.count(255)} ZERO={image.count(0)}')
        if images and image != images[0]:
            bad = next(i for i in range(SIZE) if image[i] != images[0][i])
            raise RuntimeError(f'Leituras diferentes em 0x{bad:04X}; nao salvar.')
        images.append(image)
    return images[0]

def input_image(path):
    data = Path(path).read_bytes()
    if len(data) != SIZE:
        raise RuntimeError('Use imagem de exatamente 32768 bytes. '
                           'Nao ha padding nem reorganizacao automatica.')
    return data

def text_command(s, command):
    s.write(command)
    while True:
        result = line(s)
        if result == 'END':
            break
        print(result)

def safe_disarm(s):
    try:
        s.write(b'D')
        result = line(s)
        print(result)
        return result == 'DISARMED'
    except Exception:
        print('Sem confirmacao de D: confira /CE e /OE no circuito.')
        return False

def write_image(s, data, identity):
    if not identity.endswith('PROGRAMMER'):
        raise RuntimeError('Gravacao bloqueada no firmware READER.')
    print('Circuito LM339 + MOSFETs do manual obrigatorio.')
    print('Meça VCC=6.0 V e VPP=12.5 V; /CE e /OE devem estar altos.')
    disarmed = False
    try:
        if input('Digite GRAVAR para confirmar as fontes e o chip: ') != 'GRAVAR':
            raise RuntimeError('Operacao cancelada antes de armar.')
        print('Conferindo EPROM vazia no modo de verify elevado...')
        s.write(b'A')
        if line(s) != 'ARMED':
            raise RuntimeError('Nao foi possivel armar.')
        for addr in range(0, SIZE, 128):
            block = data[addr:addr+128]
            packet = struct.pack('<HB', addr, len(block)) + block
            s.write(b'W' + packet + struct.pack('<I', zlib.crc32(packet)))
            if line(s) != 'OK':
                raise RuntimeError(f'Falha no bloco 0x{addr:04X}.')
            print(f'Verificado em tensao de programacao: {addr+128}/{SIZE}')
    finally:
        disarmed = safe_disarm(s)
        print('O comando D NAO altera fontes externas.')
        print('Baixe PRIMEIRO VPP para 5 V; DEPOIS VCC para 5 V.')
    if not disarmed:
        raise RuntimeError('Nao foi confirmado o estado seguro dos controles.')
    input('Meça ambas. Pressione Enter somente apos confirmar 5 V: ')
    actual = stable_read(s)
    if actual != data:
        bad = next(i for i in range(SIZE) if actual[i] != data[i])
        raise RuntimeError(f'Verificacao final falhou em 0x{bad:04X}.')
    print('GRAVACAO E VERIFICACAO FINAL OK.')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--porta', required=True, help='/dev/ttyACM0 ou COM3')
    p.add_argument('acao', choices=['info','teste','autoteste','vazio','ler','verificar','gravar'])
    p.add_argument('arquivo', nargs='?')
    args = p.parse_args()
    if args.acao in ('ler','verificar','gravar') and not args.arquivo:
        p.error('Esta acao exige arquivo.')
    if args.acao == 'ler' and Path(args.arquivo).exists():
        p.error('Arquivo ja existe. Escolha outro nome para preservar a copia.')
    expected = input_image(args.arquivo) if args.acao in ('verificar','gravar') else None
    with serial.Serial(args.porta,115200,timeout=60,write_timeout=10) as s:
        try:
            identity = identify(s)
            if args.acao == 'teste':
                text_command(s,b'T')
            elif args.acao == 'autoteste':
                text_command(s,b'S')
            elif args.acao == 'vazio':
                data = stable_read(s)
                print('VAZIA: todos os bytes FF.' if data == b'\xff'*SIZE
                      else 'NAO VAZIA: existem bytes diferentes de FF.')
            elif args.acao == 'ler':
                data = stable_read(s)
                with open(args.arquivo,'xb') as out:
                    out.write(data)
                print('Salvos 32768 bytes em', args.arquivo)
            elif args.acao == 'verificar':
                data = stable_read(s)
                if data != expected:
                    bad = next(i for i in range(SIZE) if data[i] != expected[i])
                    raise RuntimeError(f'Conteudo diferente em 0x{bad:04X}.')
                print('Arquivo e EPROM identicos byte a byte.')
            elif args.acao == 'gravar':
                write_image(s,expected,identity)
        finally:
            # Desabilita controles e deixa enderecos em alta impedancia.
            safe_disarm(s)
            if args.acao == 'gravar':
                print('Se ainda elevadas: baixe VPP para 5 V antes de VCC.')

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError,OSError,serial.SerialException) as exc:
        raise SystemExit('ERRO: ' + str(exc))
    except KeyboardInterrupt:
        raise SystemExit('Interrompido. Se fontes elevadas, baixe VPP antes de VCC.')
