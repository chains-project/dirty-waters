import { randomInt } from "crypto";
import { hexlify, randomBytes } from "ethers/lib/utils";
import { DkimParamsBase } from "../src/dkimParams";

describe("Test DkimParamsBase", () => {
  it("ToString And FromString Should Success", () => {
    const dkimParamsBase = new DkimParamsBase(
      hexlify(randomBytes(32)),
      randomBytes(32),
      randomInt(100),
      randomInt(100),
      randomInt(100),
      randomInt(100),
      randomInt(100),
      [hexlify(randomBytes(32))],
      hexlify(randomBytes(32)),
      [],
      randomInt(100),
      randomInt(100),
      randomInt(100),
      randomInt(100),
      randomInt(100)
    );
    const parsedDkimParamsBase = DkimParamsBase.fromString(
      dkimParamsBase.toString()
    );
    expect(dkimParamsBase.emailHeader).toEqual(
      parsedDkimParamsBase.emailHeader
    );
    expect(Buffer.from(dkimParamsBase.dkimSig).toString("hex")).toEqual(
      Buffer.from(parsedDkimParamsBase.dkimSig).toString("hex")
    );
    expect(dkimParamsBase.fromIndex).toEqual(parsedDkimParamsBase.fromIndex);
    expect(dkimParamsBase.fromLeftIndex).toEqual(
      parsedDkimParamsBase.fromLeftIndex
    );
    expect(dkimParamsBase.fromRightIndex).toEqual(
      parsedDkimParamsBase.fromRightIndex
    );
    expect(dkimParamsBase.subjectIndex).toEqual(
      parsedDkimParamsBase.subjectIndex
    );
    expect(dkimParamsBase.subjectRightIndex).toEqual(
      parsedDkimParamsBase.subjectRightIndex
    );
    dkimParamsBase.subjects.forEach((subject, i) => {
      expect(subject).toEqual(parsedDkimParamsBase.subjects[i]);
    });
    expect(dkimParamsBase.subjectPadding).toEqual(
      parsedDkimParamsBase.subjectPadding
    );
    expect(dkimParamsBase.isSubBase64).toEqual(
      parsedDkimParamsBase.isSubBase64
    );
    expect(dkimParamsBase.dkimHeaderIndex).toEqual(
      parsedDkimParamsBase.dkimHeaderIndex
    );
    expect(dkimParamsBase.sdidIndex).toEqual(parsedDkimParamsBase.sdidIndex);
    expect(dkimParamsBase.sdidRightIndex).toEqual(
      parsedDkimParamsBase.sdidRightIndex
    );
    expect(dkimParamsBase.selectorIndex).toEqual(
      parsedDkimParamsBase.selectorIndex
    );
    expect(dkimParamsBase.selectorRightIndex).toEqual(
      parsedDkimParamsBase.selectorRightIndex
    );
  });
});
