import os
import re
import random
import string

def generate_random_string(length, chars):
    return ''.join(random.choice(chars) for _ in range(length))

def replace_values(filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    grandparent_dir = os.path.dirname(parent_dir)
    target_dir = os.path.join(grandparent_dir, 'Keenetic')
    file_path = os.path.join(target_dir, filename)

    try:
        with open(file_path, 'rb') as f:
            data = f.read()
    except FileNotFoundError:
        print(f'Файл {file_path} не найден. Пожалуйста, проверьте путь к файлу.')
        return

    patterns = {
        'servicetag': (b'\x73\x65\x72\x76\x69\x63\x65\x74\x61\x67\x3D', string.digits),
        'sernumb': (b'\x73\x65\x72\x6E\x75\x6D\x62\x3D', string.digits),
        'servicepass': (b'\x73\x65\x72\x76\x69\x63\x65\x70\x61\x73\x73\x3D', string.ascii_letters + string.digits)
    }
    print ("Меняю сервисные данные...")
    print ("------------------------------------------------------------------")
    for name, (pattern, chars) in patterns.items():
        start = data.find(pattern)
        if start != -1:
            start += len(pattern)  
            end = data.find(b'\x00', start)  
            if end != -1:
                if name == 'sernumb':  
                    start = end - 4
                new_value = generate_random_string(end - start, chars).encode()
                data = data[:start] + new_value + data[end:]
                print(f'Значение переменной {name} было успешно заменено.')
            else:
                print(f'Не найдено "00" после переменной {name}.')
        else:
            print(f'Переменная {name} не найдена.')

    print ("------------------------------------------------------------------")
    new_file_path = os.path.join(target_dir, filename)
    with open(new_file_path, 'wb') as f:
        f.write(data)
        print(f'Новые данные были успешно записаны в файле {new_file_path}')
        print('')

replace_values('u-config.bin')
