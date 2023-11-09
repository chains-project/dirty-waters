import { BytesLike, constants, utils } from "ethers";
import { keccak256, solidityPack } from "ethers/lib/utils";
import { AccountLayerActionType } from ".";
import { RoleWeight } from "../key";
import { Transaction, CallType } from "../transaction";
import { subdigest } from "../utils";
import { BaseTxBuilder } from "./baseTxBuilder";

export class SyncAccountTxBuilder extends BaseTxBuilder {
  public readonly OWNER_THRESHOLD = 100;

  public readonly userAddr: string;

  public readonly keysetHash: string;

  public readonly implementation: string;

  /**
   *
   * @param userAddr The Address Of User's Smart Contract Address
   * @param metaNonce The meta nonce of Account Layer
   * @param keysetHash New KeysetHash to Update
   * @param signature Signature, default undefined
   */
  constructor(
    userAddr: BytesLike,
    public readonly metaNonce: number,
    keysetHash: BytesLike,
    public readonly timeLockDuring: number,
    implementation: BytesLike,
    signature?: BytesLike
  ) {
    super(signature);
    this.userAddr = utils.hexlify(userAddr);
    this.keysetHash = utils.hexlify(keysetHash);
    this.implementation = utils.hexlify(implementation);
  }

  /**
   *
   * @returns The Original Message For Signing
   */
  public digestMessage(): string {
    return subdigest(
      0,
      this.userAddr,
      keccak256(
        solidityPack(
          ["uint8", "uint32", "bytes32", "uint32", "address"],
          [
            AccountLayerActionType.SyncAccount,
            this.metaNonce,
            this.keysetHash,
            this.timeLockDuring,
            this.implementation,
          ]
        )
      )
    );
  }

  validateRoleWeight(roleWeight: RoleWeight): boolean {
    return roleWeight.ownerWeight >= this.OWNER_THRESHOLD;
  }

  public build(): Transaction {
    const data = this.contractInterface.encodeFunctionData("syncAccount", [
      this.metaNonce,
      this.keysetHash,
      this.timeLockDuring,
      this.implementation,
      this.signature,
    ]);

    return {
      callType: CallType.Call,
      revertOnError: true,
      gasLimit: constants.Zero,
      target: this.userAddr,
      value: constants.Zero,
      data,
    };
  }
}
