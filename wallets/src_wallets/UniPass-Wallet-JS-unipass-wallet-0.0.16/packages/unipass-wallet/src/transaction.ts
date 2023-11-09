import { BigNumber, BytesLike } from "ethers";

export enum CallType {
  Call,
  DelegateCall,
}

export interface Transaction {
  callType: CallType;
  revertOnError: boolean;
  gasLimit: BigNumber;
  target: BytesLike;
  value: BigNumber;
  data: BytesLike;
}
