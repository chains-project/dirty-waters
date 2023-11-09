import {
  KeyEmailDkim,
  KeySecp256k1,
  KeySecp256k1Wallet,
  sign,
  SignType,
} from "../src/key";
import { Keyset } from "../src/keyset";
import { BytesLike, Wallet, utils } from "ethers";
import { KeyERC1271 } from "../src/key/keyERC1271";

describe("Test Keyset", () => {
  it("Create Keyset Should Success", async () => {
    const registerEmail = "test1@gmail.com";
    const registerEmailPepper = utils.randomBytes(32);
    const masterKeyInner = Wallet.createRandom();
    const masterKeyRoleWeight = {
      ownerWeight: 40,
      guardianWeight: 60,
      assetsOpWeight: 0,
    };
    const masterKey = new KeySecp256k1(
      masterKeyInner.address,
      masterKeyRoleWeight,
      SignType.EthSign,
      async (digestHash: BytesLike): Promise<string> =>
        sign(digestHash, masterKeyInner, SignType.EthSign)
    );
    const guardian1 = new KeyERC1271(
      Wallet.createRandom().address,
      masterKeyRoleWeight
    );
    const guardian2 = new KeySecp256k1Wallet(
      Wallet.createRandom(),
      masterKeyRoleWeight,
      SignType.EIP712Sign
    );
    const keyset = Keyset.new(registerEmail, registerEmailPepper, masterKey, [
      guardian1,
      guardian2,
    ]);
    const keysetRecover = Keyset.fromJson(keyset.toJson());
    expect(keyset.keys[0]).toEqual(masterKey);
    expect(keyset.keys[1]).toEqual(
      new KeyEmailDkim(registerEmail, registerEmailPepper, {
        ownerWeight: 60,
        assetsOpWeight: 0,
        guardianWeight: 60,
      })
    );
    masterKey.signFunc = undefined;
    expect(keysetRecover.keys[0]).toEqual(masterKey);
    expect(keysetRecover.keys[1]).toEqual(keyset.keys[1]);
    expect(keysetRecover.keys[2]).toEqual(keyset.keys[2]);
    expect(keysetRecover.keys[3].roleWeight).toEqual(keyset.keys[3].roleWeight);
    expect((keysetRecover.keys[3] as KeySecp256k1Wallet).getSignType()).toEqual(
      (keyset.keys[3] as KeySecp256k1Wallet).getSignType()
    );
    expect(
      (keysetRecover.keys[3] as KeySecp256k1Wallet).wallet.address
    ).toEqual((keyset.keys[3] as KeySecp256k1Wallet).wallet.address);
  });
});
