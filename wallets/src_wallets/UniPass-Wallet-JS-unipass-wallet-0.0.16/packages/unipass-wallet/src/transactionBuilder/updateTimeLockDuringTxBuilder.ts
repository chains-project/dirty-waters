import { BytesLike, constants, utils } from "ethers";
import { keccak256, solidityPack } from "ethers/lib/utils";
import { AccountLayerActionType } from ".";
import { RoleWeight } from "../key";
import { CallType, Transaction } from "../transaction";
import { subdigest } from "../utils";
import { BaseTxBuilder } from "./baseTxBuilder";

export class UpdateTimeLockDuringTxBuilder extends BaseTxBuilder {
  public readonly OWNER_THRESHOLD = 100;

  public readonly userAddr: string;

  constructor(
    userAddr: BytesLike,
    public readonly metaNonce: number,
    public readonly timeLockDuring: number,
    signature?: BytesLike
  ) {
    super(signature);
    this.userAddr = utils.hexlify(userAddr);
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
          ["uint8", "uint32", "uint32"],
          [
            AccountLayerActionType.UpdateTimeLockDuring,
            this.metaNonce,
            this.timeLockDuring,
          ]
        )
      )
    );
  }

  validateRoleWeight(roleWeight: RoleWeight): boolean {
    return roleWeight.ownerWeight >= this.OWNER_THRESHOLD;
  }

  public build(): Transaction {
    const data = this.contractInterface.encodeFunctionData(
      "updateTimeLockDuring",
      [this.metaNonce, this.timeLockDuring, this.signature]
    );

    return {
      revertOnError: true,
      callType: CallType.Call,
      gasLimit: constants.Zero,
      target: this.userAddr,
      value: constants.Zero,
      data,
    };
  }
}
