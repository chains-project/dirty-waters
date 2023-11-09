import aes from "aes-js";
import scrypt from "scrypt-js";
import { BytesLike } from "ethers";
import {
  arrayify,
  Bytes,
  concat,
  hexlify,
  keccak256,
  randomBytes,
} from "ethers/lib/utils";
import { getPassword, looseArrayify, searchPath, uuidV4 } from "./utils";
import { pbkdf2 as _pbkdf2 } from "@ethersproject/pbkdf2";

export type ProgressCallback = (percent: number) => void;
type ScryptFunc<T> = (
  pw: Uint8Array,
  salt: Uint8Array,
  n: number,
  r: number,
  p: number,
  dkLen: number,
  callback?: ProgressCallback
) => T;
type Pbkdf2Func<T> = (
  pw: Uint8Array,
  salt: Uint8Array,
  c: number,
  dkLen: number,
  prfFunc: string
) => T;

export type EncryptOptions = {
  iv?: BytesLike;
  entropy?: BytesLike;
  client?: string;
  salt?: BytesLike;
  uuid?: string;
  scrypt?: {
    N?: number;
    r?: number;
    p?: number;
  };
};

export async function encryptKeystore(
  input: BytesLike,
  password: Bytes | string,
  options?: EncryptOptions,
  progressCallback?: ProgressCallback
): Promise<string> {
  if (typeof options === "function" && !progressCallback) {
    // eslint-disable-next-line no-param-reassign
    progressCallback = options;
    // eslint-disable-next-line no-param-reassign
    options = {};
  }

  if (!options) {
    // eslint-disable-next-line no-param-reassign
    options = {};
  }

  const inputBytes = arrayify(input);
  const passwordBytes = getPassword(password);

  // Check/generate the salt
  let salt: Uint8Array = null;

  if (options.salt) {
    salt = arrayify(options.salt);
  } else {
    salt = randomBytes(32);
  }

  // Override initialization vector
  let iv: Uint8Array = null;

  if (options.iv) {
    iv = arrayify(options.iv);

    if (iv.length !== 16) {
      throw new Error("invalid iv");
    }
  } else {
    iv = randomBytes(16);
  }

  // Override the uuid
  let uuidRandom: Uint8Array = null;

  if (options.uuid) {
    uuidRandom = arrayify(options.uuid);

    if (uuidRandom.length !== 16) {
      throw new Error("invalid uuid");
    }
  } else {
    uuidRandom = randomBytes(16);
  }

  // Override the scrypt password-based key derivation function parameters
  // eslint-disable-next-line no-bitwise
  let N = 1 << 17,
    r = 8,
    p = 1;

  if (options.scrypt) {
    if (options.scrypt.N) {
      N = options.scrypt.N;
    }

    if (options.scrypt.r) {
      r = options.scrypt.r;
    }

    if (options.scrypt.p) {
      p = options.scrypt.p;
    }
  }

  // We take 64 bytes:
  //   - 32 bytes   As normal for the Web3 secret storage (derivedKey, macPrefix)
  //   - 32 bytes   AES key to encrypt mnemonic with (required here to be Ethers Wallet)
  return scrypt
    .scrypt(passwordBytes, salt, N, r, p, 64, progressCallback)
    .then((key) => {
      // eslint-disable-next-line no-param-reassign
      key = arrayify(key);

      // This will be used to encrypt the wallet (as per Web3 secret storage)
      const derivedKey = key.slice(0, 16);
      const macPrefix = key.slice(16, 32);

      // Encrypt the private key
      const counter = new aes.Counter(iv);
      // eslint-disable-next-line new-cap
      const aesCtr = new aes.ModeOfOperation.ctr(derivedKey, counter);
      const ciphertext = arrayify(aesCtr.encrypt(inputBytes));

      // Compute the message authentication code, used to check the password
      const mac = keccak256(concat([macPrefix, ciphertext]));

      // See: https://github.com/ethereum/wiki/wiki/Web3-Secret-Storage-Definition
      const data: { [key: string]: any } = {
        id: uuidV4(uuidRandom),
        version: 3,
        Crypto: {
          cipher: "aes-128-ctr",
          cipherparams: {
            iv: hexlify(iv).substring(2),
          },
          ciphertext: hexlify(ciphertext).substring(2),
          kdf: "scrypt",
          kdfparams: {
            salt: hexlify(salt).substring(2),
            n: N,
            dklen: 32,
            p,
            r,
          },
          mac: mac.substring(2),
        },
      };

      return JSON.stringify(data);
    });
}

function _computeKdfKey<T>(
  data: any,
  password: Bytes | string,
  pbkdf2Func: Pbkdf2Func<T>,
  scryptFunc: ScryptFunc<T>,
  progressCallback?: ProgressCallback
): T {
  const passwordBytes = getPassword(password);

  const kdf = searchPath(data, "crypto/kdf");

  if (kdf && typeof kdf === "string") {
    const throwError = (name: string, value: any): never => {
      throw new Error(
        `invalid key-derivation function parameters: ${name} ${value}`
      );
    };

    if (kdf.toLowerCase() === "scrypt") {
      const salt = looseArrayify(searchPath(data, "crypto/kdfparams/salt"));
      const N = parseInt(searchPath(data, "crypto/kdfparams/n"), 10);
      const r = parseInt(searchPath(data, "crypto/kdfparams/r"), 10);
      const p = parseInt(searchPath(data, "crypto/kdfparams/p"), 10);

      // Check for all required parameters
      if (!N || !r || !p) {
        throwError("kdf", kdf);
      }

      // Make sure N is a power of 2
      // eslint-disable-next-line no-bitwise
      if ((N & (N - 1)) !== 0) {
        throwError("N", N);
      }

      const dkLen = parseInt(searchPath(data, "crypto/kdfparams/dklen"), 10);

      if (dkLen !== 32) {
        throwError("dklen", dkLen);
      }

      return scryptFunc(passwordBytes, salt, N, r, p, 64, progressCallback);
    }

    if (kdf.toLowerCase() === "pbkdf2") {
      const salt = looseArrayify(searchPath(data, "crypto/kdfparams/salt"));

      let prfFunc: string = null;
      const prf = searchPath(data, "crypto/kdfparams/prf");

      if (prf === "hmac-sha256") {
        prfFunc = "sha256";
      } else if (prf === "hmac-sha512") {
        prfFunc = "sha512";
      } else {
        throwError("prf", prf);
      }

      const count = parseInt(searchPath(data, "crypto/kdfparams/c"), 10);

      const dkLen = parseInt(searchPath(data, "crypto/kdfparams/dklen"), 10);

      if (dkLen !== 32) {
        throwError("dklen", dkLen);
      }

      return pbkdf2Func(passwordBytes, salt, count, dkLen, prfFunc);
    }
  }

  throw new Error(`unsupported key-derivation function: kdf ${kdf}`);
}

function pbkdf2Sync(
  passwordBytes: Uint8Array,
  salt: Uint8Array,
  count: number,
  dkLen: number,
  prfFunc: string
): Uint8Array {
  return arrayify(_pbkdf2(passwordBytes, salt, count, dkLen, prfFunc));
}

function pbkdf2(
  passwordBytes: Uint8Array,
  salt: Uint8Array,
  count: number,
  dkLen: number,
  prfFunc: string
): Promise<Uint8Array> {
  return Promise.resolve(
    pbkdf2Sync(passwordBytes, salt, count, dkLen, prfFunc)
  );
}

function _decrypt(
  data: any,
  key: Uint8Array,
  ciphertext: Uint8Array
): Uint8Array {
  const cipher = searchPath(data, "crypto/cipher");

  if (cipher === "aes-128-ctr") {
    const iv = looseArrayify(searchPath(data, "crypto/cipherparams/iv"));
    const counter = new aes.Counter(iv);

    // eslint-disable-next-line new-cap
    const aesCtr = new aes.ModeOfOperation.ctr(key, counter);

    return arrayify(aesCtr.decrypt(ciphertext));
  }

  return null;
}

function _getInput(data: any, key: Uint8Array): string {
  const ciphertext = looseArrayify(searchPath(data, "crypto/ciphertext"));

  const computedMAC = hexlify(
    keccak256(concat([key.slice(16, 32), ciphertext]))
  ).substring(2);

  if (computedMAC !== searchPath(data, "crypto/mac").toLowerCase()) {
    throw new Error("invalid password");
  }

  const input = _decrypt(data, key.slice(0, 16), ciphertext);

  return hexlify(input);
}

export async function decryptKeystore(
  json: string,
  password: Bytes | string,
  progressCallback?: ProgressCallback
): Promise<string> {
  const data = JSON.parse(json);

  const key = await _computeKdfKey(
    data,
    password,
    pbkdf2,
    scrypt.scrypt,
    progressCallback
  );

  return _getInput(data, key);
}
