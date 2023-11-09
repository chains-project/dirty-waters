import { KeyBase } from "./key";
import { BytesLike, utils } from "ethers";

export function getKeysetHash(keys: KeyBase[]): string {
  let keysetHash = "0x";
  keys.forEach((key) => {
    keysetHash = utils.keccak256(
      utils.solidityPack(["bytes", "bytes"], [keysetHash, key.serialize()])
    );
  });

  return keysetHash;
}

export function subdigest(
  chainId: number,
  address: string,
  hash: BytesLike
): string {
  return utils.keccak256(
    utils.solidityPack(
      ["bytes", "uint256", "address", "bytes32"],
      [Buffer.from("\x19\x01"), chainId, address, hash]
    )
  );
}
