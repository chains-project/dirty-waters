import { DkimParamsBase, Signature } from "unipass-wallet-dkim-base";
import * as Dkim from "dkim";

const mailParser = require("mailparser");

export function verifyDKIMContent(content: Buffer) {
  return new Promise((resolve, reject) => {
    Dkim.verify(content, false, (err, result) => {
      if (err) {
        reject(err);
      } else {
        resolve(result);
      }
    });
  });
}

export class DkimParams extends DkimParamsBase {
  /**
   *
   * @param _emailHeader The original message For Dkim, UTF8 string or Uint8Array
   * @param dkimSig The Dkim Signature
   * @param fromIndex The From Header Index Of emailHeader
   * @param fromLeftIndex The Start Index Of From Email Address in the From Header
   * @param fromRightIndex The End Index Of From Email Address in the From Header
   * @param subjectIndex The Start Index Of Subject Header
   * @param subjectRightIndex The End Index Of Suject Header
   * @param subject The subject parts
   * @param subjectPadding The subject prefix padding
   * @param isSubBase64 Is base64 encoded for subject parts
   * @param dkimHeaderIndex The start Index of Dkim Header
   * @param sdidIndex The Start Index Of Sdid
   * @param sdidRightIndex The End Index Of Sdid
   * @param selectorIndex The Start Index Of Selector
   * @param selectorRightIndex The End Index Of Selector
   */
  constructor(
    emailHeader: string,
    dkimSig: Uint8Array,
    fromIndex: number,
    fromLeftIndex: number,
    fromRightIndex: number,
    subjectIndex: number,
    subjectRightIndex: number,
    subject: string[],
    subjectPadding: string,
    isSubBase64: boolean[],
    dkimHeaderIndex: number,
    sdidIndex: number,
    sdidRightIndex: number,
    selectorIndex: number,
    selectorRightIndex: number
  ) {
    super(
      emailHeader,
      dkimSig,
      fromIndex,
      fromLeftIndex,
      fromRightIndex,
      subjectIndex,
      subjectRightIndex,
      subject,
      subjectPadding,
      isSubBase64,
      dkimHeaderIndex,
      sdidIndex,
      sdidRightIndex,
      selectorIndex,
      selectorRightIndex
    );
  }

  public static getDkimParams(
    results: Dkim.VerifyResult[],
    subs: string[],
    isSubBase64: boolean[],
    subjectPadding: string,
    fromHeader: string,
    emailBlackList: string[]
  ): DkimParams {
    if (isSubBase64.length === 0) {
      isSubBase64.push(false);
    }
    const params = results
      .map((result): DkimParams | undefined => {
        const { processedHeader } = result;
        const fromIndex = processedHeader.indexOf("from:");
        const fromEndIndex = processedHeader.indexOf("\r\n", fromIndex);

        let fromLeftIndex = processedHeader.indexOf(
          `<${fromHeader}>`,
          fromIndex
        );

        if (fromLeftIndex === -1 || fromLeftIndex > fromEndIndex) {
          fromLeftIndex = processedHeader.indexOf(fromHeader);
        } else {
          fromLeftIndex += 1;
        }
        const fromRightIndex = fromLeftIndex + fromHeader.length - 1;

        const signature = result.signature as any as Signature;

        if (emailBlackList.includes(signature.domain)) {
          return undefined;
        }

        const subjectIndex = processedHeader.indexOf("subject:");
        const dkimHeaderIndex = processedHeader.indexOf("dkim-signature:");
        const sdidIndex = processedHeader.indexOf(
          signature.domain,
          dkimHeaderIndex
        );
        const sdidRightIndex = sdidIndex + signature.domain.length;
        const selectorIndex = processedHeader.indexOf(
          signature.selector,
          dkimHeaderIndex
        );
        const selectorRightIndex = selectorIndex + signature.selector.length;

        return new DkimParams(
          processedHeader,
          signature.signature,
          fromIndex,
          fromLeftIndex,
          fromRightIndex,
          subjectIndex,
          processedHeader.indexOf("\r\n", subjectIndex),
          subs,
          subjectPadding,
          isSubBase64,
          dkimHeaderIndex,
          sdidIndex,
          sdidRightIndex,
          selectorIndex,
          selectorRightIndex
        );
      })
      .find((v) => v !== undefined);

    return params;
  }

  public static async parseEmailParams(
    email: string,
    emailBlackList: string[]
  ): Promise<DkimParams> {
    const mail = await mailParser.simpleParser(email, {
      subjectSep: " ",
      isSepBase64: true,
    });

    const subs = {
      subs: [],
      subsAllLen: 0,
      subjectPadding: "",
      subIsBase64: [],
    };
    mail.subParser.forEach((s: string, index: number) => {
      this.dealSubPart(index, s, mail.isSubBase64, subs);
    });

    const from = mail.headers.get("from").value[0].address;
    const results: Dkim.VerifyResult[] = (await verifyDKIMContent(
      Buffer.from(email, "utf-8")
    )) as Dkim.VerifyResult[];

    return this.getDkimParams(
      results,
      subs.subs,
      subs.subIsBase64,
      subs.subjectPadding,
      from,
      emailBlackList
    );
  }
}
