import { BytesLike, utils, Wallet } from "ethers";

export * from "./keyBase";

export * from "./keySecp256k1";

export * from "./keySecp256k1Wallet";

export * from "./keyEmailDkim";

export enum KeyType {
  Secp256k1,
  ERC1271Wallet,
  EmailDkim,
}

export enum SignType {
  EIP712Sign = 1,
  EthSign = 2,
}

export enum SignFlag {
  NotSign = 0,
  Sign = 1,
}

export interface RoleWeight {
  ownerWeight: number;
  assetsOpWeight: number;
  guardianWeight: number;
}

export function serializeRoleWeight(roleWeight: RoleWeight): string {
  return utils.solidityPack(
    ["uint32", "uint32", "uint32"],
    [
      roleWeight.ownerWeight,
      roleWeight.assetsOpWeight,
      roleWeight.guardianWeight,
    ]
  );
}

export async function ethSign(
  message: BytesLike,
  key: Wallet
): Promise<string> {
  return key.signMessage(utils.arrayify(message));
}

export function eip712Sign(_hash: BytesLike, _key: Wallet): string {
  const sig = utils.joinSignature(
    _key._signingKey().signDigest(utils.arrayify(_hash))
  );

  return sig;
}

export async function sign(
  hash: BytesLike,
  key: Wallet,
  signType: SignType
): Promise<string> {
  let sig;

  switch (signType) {
    case SignType.EIP712Sign: {
      sig = await eip712Sign(hash, key);
      break;
    }

    case SignType.EthSign: {
      sig = await ethSign(hash, key);
      break;
    }

    default: {
      const error: any = new Error(`Invalid SignTyp: ${signType}`);
      error.signType = signType;
      throw error;
    }
  }

  return utils.solidityPack(["bytes", "uint8"], [sig, signType]);
}
