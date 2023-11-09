import { DkimParamsBase, pureEmailHash } from "unipass-wallet-dkim-base";
import { KeyType, RoleWeight, SignFlag } from ".";
import { KeyBase } from "./keyBase";
import { BytesLike, utils } from "ethers";

export class KeyEmailDkim extends KeyBase {
  public readonly pepper: string;

  constructor(
    public readonly emailFrom: string,
    _pepper: BytesLike,
    roleWeight: RoleWeight,
    private dkimParams?: DkimParamsBase
  ) {
    super(roleWeight);

    if (
      this.dkimParams !== undefined &&
      this.emailFrom !==
        this.dkimParams.emailHeader.slice(
          this.dkimParams.fromLeftIndex,
          this.dkimParams.fromRightIndex + 1
        )
    ) {
      throw new Error("Not Matched DkimParams With Email Address");
    }
    this.pepper = utils.hexlify(_pepper);
  }

  public toJson() {
    return JSON.stringify({
      emailFrom: this.emailFrom,
      pepper: this.pepper,
      roleWeight: this.roleWeight,
      dkimParams: this.dkimParams
        ? this.dkimParams.toJsonObj()
        : this.dkimParams,
    });
  }

  static fromJsonObj(obj: any): KeyEmailDkim {
    return new KeyEmailDkim(
      obj.emailFrom,
      obj.pepper,
      obj.roleWeight,
      obj.dkimParams
        ? DkimParamsBase.fromJsonObj(obj.dkimParams)
        : obj.dkimParams
    );
  }

  public getDkimParams(): DkimParamsBase | undefined {
    return this.dkimParams;
  }

  public setDkimParams(v: DkimParamsBase) {
    const emailFrom = v.emailHeader.slice(
      v.fromLeftIndex,
      v.fromRightIndex + 1
    );

    if (this.emailFrom !== emailFrom) {
      throw new Error("Not Matched EmailFrom And DkimParams");
    }
    this.dkimParams = v;
  }

  public async generateSignature(digestHash: string): Promise<string> {
    if (this.dkimParams === undefined) {
      throw new Error("Expected DkimParams");
    }
    const subject = this.dkimParams.subjectPadding.concat(
      this.dkimParams.subjects.join("")
    );

    if (subject !== digestHash) {
      throw new Error(`Expected subject ${subject}, got ${digestHash}`);
    }

    return utils.solidityPack(
      ["uint8", "uint8", "bytes32", "bytes", "bytes"],
      [
        KeyType.EmailDkim,
        SignFlag.Sign,
        this.pepper,
        this.dkimParams.serialize(),
        this.serializeRoleWeight(),
      ]
    );
  }

  public generateKey(): string {
    return utils.solidityPack(
      ["uint8", "uint8", "bytes32", "bytes"],
      [
        KeyType.EmailDkim,
        SignFlag.NotSign,
        pureEmailHash(this.emailFrom, this.pepper),
        this.serializeRoleWeight(),
      ]
    );
  }

  public serialize(): string {
    return utils.solidityPack(
      ["uint8", "bytes32", "bytes"],
      [
        KeyType.EmailDkim,
        pureEmailHash(this.emailFrom, this.pepper),
        this.serializeRoleWeight(),
      ]
    );
  }
}
