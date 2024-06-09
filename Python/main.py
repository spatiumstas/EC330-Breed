import os
import sys
import shutil
import time
import socket
import paramiko
import gateway
import filecmp
from scp import SCPClient
from getpass import getpass

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Data')

def get_hex_offset(filename, offset, length):
    with open(filename, 'rb') as f:
        f.seek(offset)
        return f.read(length).hex()

def get_mtd_partitions(client):
    stdin, stdout, stderr = client.exec_command('cat /proc/mtd')
    data = stdout.read().decode()
    lines = data.split('\n')
    partitions = {}
    for line in lines:
        if 'u-boot' in line:
            partitions['u-boot'] = line.split(':')[0]
        elif 'factory' in line:
            partitions['factory'] = line.split(':')[0]
    return partitions

def get_mac_address(file_path):
    with open(file_path, "rb") as f:
        data = bytearray(f.read())

    mac_address_pattern = b'FlashMac val='
    start = data.find(mac_address_pattern)
    if start != -1:
        mac_address = data[start + len(mac_address_pattern):start + len(mac_address_pattern) + 17]
        return mac_address.replace(b':', b'').decode()
    else:
        print('MAC-адрес не найден')
        return

def increment_mac_address(mac_address):
    mac_int = int(mac_address, 16)
    mac_int += 1
    return format(mac_int, '012x')

def zero_byte(file, offset):
    file.seek(offset)
    file.write(b'\x00')

def extract_wifi_calibrations(input_file_path, output_file_path):
    print('')
    print('Модификацирую EEPROM...')
    time.sleep(1)
    with open(input_file_path, "rb") as f:
        data = bytearray(f.read())

    mac_address_pattern = b'FlashMac val='
    start = data.find(mac_address_pattern)
    if start != -1:
        mac_address = data[start + len(mac_address_pattern):start + len(mac_address_pattern) + 17]
        mac_address = mac_address.replace(b':', b'').decode()
    else:
        print('MAC-адрес не найден')
        return

    wifi_calibrations_pattern = b'\x15\x76\xA0\x00'
    start = data.find(wifi_calibrations_pattern)
    if start != -1:
        wifi_calibrations1 = data[start:start + 0x2600]
        print('Найдена первая калибровка Wi-Fi')
        time.sleep(2)
        print('А вторая?')
    else:
        print('Первая калибровка Wi-Fi не найдена')
        return

    start2 = data.find(wifi_calibrations_pattern, start + 0x2600)
    if start2 != -1:
        wifi_calibrations2 = data[start2:start2 + 0x2600]
        print('Найдена вторая калибровка Wi-Fi')
        time.sleep(2)
        print('А вот и она')
    else:
        print('Вторая калибровка Wi-Fi не найдена')
        return

    with open(output_file_path, "wb") as f:
        f.write(wifi_calibrations1)
        f.write(b'\xFF' * (0x8000 - f.tell()))
        f.write(wifi_calibrations2)
        f.write(b'\xFF' * (512 * 1024 - f.tell()))

    with open(output_file_path, "r+b") as f:
        offsets = [0x4, 0x28, 0x8004, 0x8028]
        original_mac_address = mac_address
        for i, offset in enumerate(offsets):
            f.seek(offset)
            if i == 1:
                f.write(bytes.fromhex(original_mac_address))
            else:
                f.write(bytes.fromhex(increment_mac_address(mac_address)))
                mac_address = increment_mac_address(mac_address)

        zero_byte(f, 0x52)
        zero_byte(f, 0x8052)
        print('Разгоняю процессор...')
        time.sleep(3)
        print('Перенастраиваю поток воздуха...')
        time.sleep(2)
        print('Щепотку соли...')
        time.sleep(2)

    return output_file_path

def move_modified_file(output_file_path):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    grandparent_dir = os.path.dirname(parent_dir)
    target_dir = os.path.join(grandparent_dir, 'Keenetic')
    modified_file_path = os.path.join(target_dir, os.path.basename(output_file_path))

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    shutil.move(output_file_path, modified_file_path)
    print(f'Модификация завершена, EEPROM был успешно помещён в папку Keenetic: {modified_file_path}')

def backup(client, partitions):
    commands = [
        (f'dd if=/dev/mtd0 of=/tmp/u-boot_stock.bin', 'u-boot_stock.bin'),
        (f'dd if=/dev/{partitions["factory"]} of=/tmp/OpenWrt.EEPROM.bin', 'OpenWrt.EEPROM.bin')
    ]
    for command, filename in commands:
        stdin, stdout, stderr = client.exec_command(command, get_pty=True)
        time.sleep(2)
        data = stdout.read() + stderr.read()
        scp = SCPClient(client.get_transport())
        scp.get(f'/tmp/{filename}', os.path.join(DATA_DIR, filename))
        if filename == 'OpenWrt.EEPROM.bin':
            mac_address = get_mac_address(os.path.join(DATA_DIR, filename))
            if mac_address is not None:
                new_filename = 'EEPROM_' + mac_address.upper() + '.bin'
            shutil.copy(os.path.join(DATA_DIR, filename), os.path.join(DATA_DIR, new_filename))
            if filecmp.cmp(os.path.join(DATA_DIR, filename), os.path.join(DATA_DIR, new_filename)):
                os.remove(os.path.join(DATA_DIR, filename))
            filename = new_filename
        if os.path.exists(os.path.join(DATA_DIR, filename)):
            if filename == 'u-boot_stock.bin':
                print(f'Стоковый загрузчик {filename} успешно сохранен в папку Data')
            else:
                print(f'{filename} успешно сохранен в папку Data')
                modified_file_path = extract_wifi_calibrations(os.path.join(DATA_DIR, filename), os.path.join(DATA_DIR, new_filename))
                move_modified_file(modified_file_path)
        else:
            print(f'Ошибка при сохранении {filename}')

def write_loader(client):
    stdin, stdout, stderr = client.exec_command('insmod mtd-rw i_want_a_brick=1')
    scp = SCPClient(client.get_transport())
    scp.put(os.path.join(DATA_DIR, 'Breed_EC330.bin'), '/tmp/Breed_EC330.bin')
    stdin, stdout, stderr = client.exec_command('mtd write /tmp/Breed_EC330.bin u-boot', get_pty=True)
    time.sleep(2)
    data = stdout.read() + stderr.read()

def main():
    print(f"+---------------------------------------------------+")
    print("|     Breed installer for EC330 by spatiumstas      |")
    print(f"+---------------------------------------------------+")

    router_ip = gateway.get_ip_address()
    username = 'root'
    password = 'root'
    ssh_port = '22'

    try:
        with paramiko.SSHClient() as client:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=router_ip, username=username, password=password, port=ssh_port)
            time.sleep(2)
            partitions = get_mtd_partitions(client)
            backup(client, partitions)
            write_loader(client)
            print("")
            print(f"+-------------------------------------------------------------+")
            print("|              Загрузчик Breed успешно установлен             |")
            print(f"+-------------------------------------------------------------+")
            print("")
            print('Перезагрузка в Breed...')
            client.exec_command('reboot')
            time.sleep(2)
            client.close()
            sys.exit()
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
