import {
  KeySecp256k1,
  KeyEmailDkim,
  RoleWeight,
  KeyBase,
  KeySecp256k1Wallet,
} from "./key";
import { KeyERC1271 } from "./key/keyERC1271";
import { getKeysetHash } from "./utils";
import { BytesLike } from "ethers";

export class Keyset {
  /**
   * @dev This class is used for Unipass-Wallet. If users changed their keysetHashs, this class may lose efficacy.
   *      Keys are sorted by `[MasterKey, RegisterEmailKey, Guardians, Policy]`
   * @param keys Inner Keys.
   */
  constructor(public readonly keys: KeyBase[]) {}

  static new(
    registerEmail: string,
    registerEmailPepper: BytesLike,
    masterKey: KeySecp256k1,
    guardians: KeyBase[],
    policy?: KeyBase,
    registerEmailRoleWeight?: RoleWeight
  ): Keyset {
    const registerEmailKey = new KeyEmailDkim(
      registerEmail,
      registerEmailPepper,
      registerEmailRoleWeight || {
        ownerWeight: 60,
        assetsOpWeight: 0,
        guardianWeight: 60,
      }
    );
    const keys = [masterKey as KeyBase, registerEmailKey].concat(guardians);

    if (policy) {
      keys.push(policy);
    }

    return new Keyset(keys);
  }

  public hash(): string {
    return getKeysetHash(this.keys);
  }

  public toJson(): string {
    return `[${this.keys
      .map((v) => {
        if (v instanceof KeyEmailDkim) {
          return `{"KeyEmailDkim":${v.toJson()}}`;
        }

        if (v instanceof KeyERC1271) {
          return `{"KeyERC1271":${v.toJson()}}`;
        }

        if (v instanceof KeySecp256k1) {
          return `{"KeySecp256k1":${v.toJson()}}`;
        }

        if (v instanceof KeySecp256k1Wallet) {
          return `{"KeySecp256k1Wallet":${v.toJson()}}`;
        }
        throw new Error("Not Valid KeyBase");
      })
      .join(",")}]`;
  }

  public static fromJson(json: string): Keyset {
    return new Keyset(
      (JSON.parse(json) as any[]).map((v) => {
        if (v.KeyEmailDkim) {
          return KeyEmailDkim.fromJsonObj(v.KeyEmailDkim);
        }

        if (v.KeyERC1271) {
          return KeyERC1271.fromJsonObj(v.KeyERC1271);
        }

        if (v.KeySecp256k1) {
          return KeySecp256k1.fromJsonObj(v.KeySecp256k1);
        }

        if (v.KeySecp256k1Wallet) {
          return KeySecp256k1Wallet.fromJsonObj(v.KeySecp256k1Wallet);
        }
        throw new Error("Invalid KeyBase");
      })
    );
  }
}
