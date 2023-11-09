import { BytesLike, utils, Wallet } from "ethers";
import { KeyBase, sign, SignType } from "./key";
import { IPermit } from "./permit";
import { subdigest } from "./utils";

export class SessionKey {
  public userAddr: string;

  constructor(
    public readonly wallet: Wallet,
    public signType: SignType,
    public chainId: number,
    _userAddr: BytesLike,
    public permit?: IPermit
  ) {
    this.userAddr = utils.hexlify(_userAddr);
  }

  public digestPermitMessage(timestamp: number, weight: number): string {
    return subdigest(
      this.chainId,
      this.userAddr,
      utils.keccak256(
        utils.solidityPack(
          ["address", "uint32", "uint32"],
          [this.wallet.address, timestamp, weight]
        )
      )
    );
  }

  public async generatePermit(
    timestamp: number,
    weight: number,
    selectedKeys: [KeyBase, boolean][]
  ): Promise<SessionKey> {
    const permitDigestHash = this.digestPermitMessage(timestamp, weight);

    const permitParts: [number, string][] = await Promise.all(
      selectedKeys.map(async ([key, isSig]) => {
        if (isSig) {
          return [
            key.roleWeight.assetsOpWeight,
            await key.generateSignature(permitDigestHash),
          ];
        }

        return [0, key.generateKey()];
      })
    );

    const selectedWeight = permitParts
      .map((v) => v[0])
      .reduce((previous, current) => previous + current);

    if (selectedWeight < weight) {
      throw new Error(
        `Expected Key Weight[${weight}], Less than ${selectedWeight}`
      );
    }

    const permit = utils.hexlify(utils.concat(permitParts.map((v) => v[1])));
    this.permit = {
      timestamp,
      weight,
      permit,
    };

    return this;
  }

  public async generateSignature(digestHash: string): Promise<string> {
    return utils.solidityPack(
      ["uint32", "uint32", "bytes", "bytes"],
      [
        this.permit!.timestamp,
        this.permit!.weight,
        await sign(digestHash, this.wallet, this.signType),
        this.permit!.permit,
      ]
    );
  }
}
