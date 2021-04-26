#!/usr/bin/env python3
import sys
import rsa
from os import path, makedirs
from yaml import safe_load, YAMLError

def read_config(config_path):
    with open(path.join(config_path, 'config.yaml'),'r') as f:
        try:
            config = safe_load(f)
        except YAMLError as exc:
            print(f"Error with config.yaml file {str(exc)}")
    return config

def generate_pem(save_path, nbits=1024):
    if not path.exists(save_path):
        makedirs(save_path)

    if (path.exists(path.join(save_path,'private.pem'))):
        print("Keys already created, nothing changed.")
        return
    publicKey, privateKey = rsa.newkeys(nbits)
    public_pem = path.join(save_path, 'public.pem')
    private_pem = path.join(save_path, 'private.pem')
    try:
        with open(public_pem, 'w+') as fp:
            fp.write(publicKey.save_pkcs1().decode())
        with open(private_pem, 'w+') as fp:
            fp.write(privateKey.save_pkcs1().decode())
    except Exception as ex:
        print(f"Error occurred: {str(ex)}")


if __name__ == "__main__":
    config_path = sys.argv[1]
    config = read_config(config_path)
    save_path = config.get('encryption').get('save_path')
    generate_pem(save_path)
    print(f"Public and Private Keys generated in location {save_path}")
