"""Install a checksum-pinned official Windows utility; initial setup only."""
import hashlib
import io
import zipfile
from urllib.request import urlopen
from app.storage import ROOT

URL='https://breakfastquay.com/files/releases/rubberband-4.0.0-gpl-executable-windows.zip'
SHA256='f2d47fc64dbb42f6cc62edf7933ac4fa89d8f0ef8b9cf97b6afc263a7fe05644'


def main():
    target=ROOT/'tools/rubberband'
    with urlopen(URL,timeout=60) as response:
        archive=response.read()
    if hashlib.sha256(archive).hexdigest()!=SHA256:
        raise ValueError('Rubber Band download checksum mismatch; nothing installed.')
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        for item in package.infolist():
            resolved=(target/item.filename).resolve()
            if not resolved.is_relative_to(target.resolve()):
                raise ValueError('Unsafe archive path.')
        target.mkdir(parents=True,exist_ok=True)
        package.extractall(target)
    print('Rubber Band 4.0 installed with official license and notices.')


if __name__=='__main__': main()
