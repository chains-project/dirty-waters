import { Contract, Overrides, utils } from "ethers";
import { defaultAbiCoder, keccak256, solidityPack } from "ethers/lib/utils";
import { KeyBase } from "./key";
import { SessionKey } from "./sessionKey";
import { Transaction } from "./transaction";
import { subdigest } from "./utils";

export class TxExcutor {
  /**
   *
   * @param chainId The Chain ID Of Blockchain
   * @param nonce The Nonce of Transaction
   * @param txs  Transactions To executed
   * @param signature Signature From U
   */
  constructor(
    public chainId: number,
    public contract: Contract,
    public nonce: number,
    public txs: Transaction[],
    public signature?: string
  ) {}

  /**
   *
   * @returns The Original Message For Signing
   */
  public digestMessage(): string {
    return subdigest(
      this.chainId,
      this.contract.address,
      keccak256(
        defaultAbiCoder.encode(
          [
            "uint256",
            "tuple(uint8 callType,bool revertOnError,address target,uint256 gasLimit,uint256 value,bytes data)[]",
          ],
          [this.nonce, this.txs]
        )
      )
    );
  }

  public async generateSignature(
    keyOrSessionKey: [KeyBase, boolean][] | SessionKey
  ): Promise<TxExcutor> {
    const digestHash = this.digestMessage();
    let sig;

    if (keyOrSessionKey instanceof SessionKey) {
      const isSessionKey = 1;
      sig = solidityPack(
        ["uint8", "bytes"],
        [isSessionKey, await keyOrSessionKey.generateSignature(digestHash)]
      );
    } else if (keyOrSessionKey.length === 0) {
      sig = "0x";
    } else {
      const isSessionKey = 0;
      sig = solidityPack(
        ["uint8", "bytes"],
        [
          isSessionKey,
          utils.concat(
            await Promise.all(
              keyOrSessionKey.map(async ([key, isSig]) => {
                if (isSig) {
                  const ret = await key.generateSignature(digestHash);

                  return ret;
                }

                return key.generateKey();
              })
            )
          ),
        ]
      );
    }

    this.signature = sig;

    return this;
  }

  /**
   *
   * @param contract The Contract Of Proxy ModuleMain
   * @param executeOpt Transaction Options
   * @returns Eth Transaction Info
   */
  public async execute(executeOpt: Overrides | undefined) {
    if (this.signature === undefined) {
      throw new Error(`expected generating signature`);
    }

    return this.contract.execute(
      this.txs,
      this.nonce,
      this.signature,
      executeOpt
    );
  }
}
