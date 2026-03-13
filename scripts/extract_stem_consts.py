import zipfile, os, struct

def read_strings(data):
    strings = []
    i = 0
    while i < len(data) - 3:
        if data[i] == 1:
            length = (data[i+1] << 8) | data[i+2]
            if 3 < length < 200:
                s = data[i+3:i+3+length]
                try:
                    decoded = s.decode('utf-8')
                    strings.append(decoded)
                except Exception:
                    pass
            i += 3 + length
        else:
            i += 1
    return strings

os.makedirs('tmp_stems', exist_ok=True)
keywords_lower = ['max', 'high', 'width', 'length', 'count', 'gap', 'stem', 'seed']
targets = ['StemScaler', 'StemBuild', 'StemCheck', 'Scale_StemScale', 'StemHori']

with zipfile.ZipFile('C:/Program Files/Audiveris/app/audiveris.jar') as z:
    for n in z.namelist():
        base = n.replace('/', '_').replace('$', '_')
        if any(t in base for t in targets):
            data = z.read(n)
            out = 'tmp_stems/' + base
            open(out, 'wb').write(data)
            strings = read_strings(data)
            print(f'=== {n} ===')
            for s in strings:
                if any(k in s.lower() for k in keywords_lower):
                    print('  ', s)
            print()
