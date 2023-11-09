import { BytesLike } from "ethers";
import { sha256, solidityPack, toUtf8Bytes } from "ethers/lib/utils";

export function emailHash(
  inputEmailAddress: string,
  pepper: BytesLike
): string {
  if (!inputEmailAddress) {
    throw new Error("Email Address is None");
  }
  let emailAddress = inputEmailAddress.toLowerCase();
  const split = emailAddress.split("@", 2);

  if (
    split[1] === "gmail.com" ||
    split[1] === "googlemail.com" ||
    split[1] === "protonmail.com" ||
    split[1] === "ptoton.me" ||
    split[1] === "pm.me"
  ) {
    emailAddress = split[0].replace(".", "").concat("@", split[1]);
  }

  return pureEmailHash(emailAddress, pepper);
}

/**
 *
 * @param emailAddress The Email Address
 * @returns ZK Hash For Email Address
 */
export function pureEmailHash(emailAddress: string, pepper: BytesLike): string {
  return sha256(
    solidityPack(["bytes", "bytes32"], [toUtf8Bytes(emailAddress), pepper])
  );
}
