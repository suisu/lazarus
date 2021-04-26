from os import path
import rsa
from config import Settings

def get_priv_keys():
    save_path = Settings.config.get('encryption').get('save_path')
    with open(path.join(save_path, 'private.pem')) as privfile:
        keydata = privfile.read()
    privkey = rsa.PrivateKey.load_pkcs1(keydata, 'PEM')
    return privkey

def get_pub_keys():
    save_path = Settings.config.get('encryption').get('save_path')
    with open(path.join(save_path, 'public.pem')) as pubfile:
        keydata = pubfile.read()
    pubkey = rsa.PublicKey.load_pkcs1(keydata, 'PEM')
    return pubkey