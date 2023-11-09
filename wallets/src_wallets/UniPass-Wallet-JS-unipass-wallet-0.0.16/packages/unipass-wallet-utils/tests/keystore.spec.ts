import { hexlify } from "ethers/lib/utils";
import { decryptKeystore, encryptKeystore } from "../src/keystore";

describe("Test KeyStore", () => {
  it("Enscript And Descript Should Seccess", async () => {
    const input = hexlify(Buffer.from("input"));
    const password = "password";
    const keystore = await encryptKeystore(input, password);
    expect(await decryptKeystore(keystore, password)).toEqual(input);
  });
});
