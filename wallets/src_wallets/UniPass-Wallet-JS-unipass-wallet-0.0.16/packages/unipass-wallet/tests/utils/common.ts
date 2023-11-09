import {
  getCreate2Address,
  keccak256,
  randomBytes,
  solidityPack,
} from "ethers/lib/utils";
import { DkimParams } from "unipass-wallet-dkim";
import MailComposer from "nodemailer/lib/mail-composer";
import DKIM from "nodemailer/lib/dkim";
import { BigNumber, ethers, Wallet } from "ethers";
import {
  KeyBase,
  KeyEmailDkim,
  KeySecp256k1Wallet,
  RoleWeight,
  SignType,
} from "../../src/key";

export const optimalGasLimit = ethers.constants.Two.pow(21);

export enum Role {
  Owner,
  AssetsOp,
  Guardian,
}

function randomInt(max: number) {
  return Math.ceil(Math.random() * (max + 1));
}

export function randomKeys(len: number): KeyBase[] {
  const ret: KeyBase[] = [];

  for (let i = 0; i < len; i++) {
    [Role.Owner, Role.AssetsOp, Role.Guardian].forEach((role) => {
      const random = randomInt(1);

      if (random === 0) {
        ret.push(
          new KeySecp256k1Wallet(
            Wallet.createRandom(),
            randomRoleWeight(role, len),
            SignType.EthSign
          )
        );
      } else {
        ret.push(
          new KeyEmailDkim(
            `${Buffer.from(randomBytes(10)).toString("hex")}@unipass.com`,
            randomBytes(32),
            randomRoleWeight(role, len)
          )
        );
      }
    });
  }

  return ret;
}

export function randomRoleWeight(role: Role, len: number): RoleWeight {
  const v = Math.ceil(100 / len);

  switch (role) {
    case Role.Owner: {
      return {
        ownerWeight: randomInt(50 - v) + v,
        assetsOpWeight: 0,
        guardianWeight: 0,
      };
    }

    case Role.AssetsOp: {
      return {
        ownerWeight: 0,
        assetsOpWeight: randomInt(50 - v) + v,
        guardianWeight: 0,
      };
    }

    case Role.Guardian: {
      return {
        ownerWeight: 0,
        assetsOpWeight: 0,
        guardianWeight: randomInt(50 - v) + v,
      };
    }

    default: {
      throw new Error(`Invalid Role: ${role}`);
    }
  }
}

export async function selectKeys(
  keys: KeyBase[],
  subject: string,
  unipassPrivateKey: string,
  role: Role,
  threshold: number
): Promise<[KeyBase, boolean][]> {
  const indexes: number[] = [];
  let sum = 0;
  keys
    .map((v, i) => {
      let value;

      if (role === Role.Owner) {
        value = v.roleWeight.ownerWeight;
      } else if (role === Role.AssetsOp) {
        value = v.roleWeight.assetsOpWeight;
      } else if (role === Role.Guardian) {
        value = v.roleWeight.guardianWeight;
      } else {
        throw new Error(`Invalid Role: ${role}`);
      }

      return { index: i, value };
    })
    .sort((a, b) => b.value - a.value)
    .forEach((v) => {
      if (sum < threshold) {
        indexes.push(v.index);
        sum += v.value;
      }
    });
  const ret: [KeyBase, boolean][] = await Promise.all(
    keys.map(async (key, i) => {
      if (indexes.includes(i)) {
        if (key instanceof KeyEmailDkim) {
          const dkimParams = await generateDkimParams(
            key.emailFrom,
            subject,
            unipassPrivateKey
          );
          // eslint-disable-next-line no-param-reassign
          key.setDkimParams(dkimParams);
        }

        return [key, true];
      }

      return [key, false];
    })
  );

  return ret;
}

export function getKeysetHash(keys: KeyBase[]): string {
  let keysetHash = "0x";
  keys.forEach((key) => {
    keysetHash = keccak256(
      solidityPack(["bytes", "bytes"], [keysetHash, key.serialize()])
    );
  });

  return keysetHash;
}

export function getProxyAddress(
  moduleMainAddress: string,
  dkimKeysAddress: string,
  factoryAddress: string,
  keysetHash: string
): string {
  const code = ethers.utils.solidityPack(
    ["bytes", "uint256"],
    [
      "0x603a600e3d39601a805130553df3363d3d373d3d3d363d30545af43d82803e903d91601857fd5bf3",
      moduleMainAddress,
    ]
  );
  const codeHash = keccak256(code);
  const salt = keccak256(
    solidityPack(["bytes32", "address"], [keysetHash, dkimKeysAddress])
  );
  const expectedAddress = getCreate2Address(factoryAddress, salt, codeHash);

  return expectedAddress;
}

export async function getSignEmailWithDkim(
  subject: string,
  from: string,
  to: string,
  unipassPrivateKey: string
) {
  const mail = new MailComposer({
    from,
    to,
    subject,
    html: "<b>Unipass Test</b>",
  });

  const dkim = new DKIM({
    keySelector: "s2055",
    domainName: "unipass.com",
    privateKey: unipassPrivateKey,
  });
  const email = await signEmailWithDkim(mail, dkim);

  return email;
}

export async function signEmailWithDkim(mail: MailComposer, dkim: DKIM) {
  const msg = await mail.compile().build();
  const signedMsg = dkim.sign(msg);
  let buff = "";

  // eslint-disable-next-line no-restricted-syntax
  for await (const chunk of signedMsg) {
    buff += chunk;
  }

  return buff;
}

export async function generateDkimParams(
  emailFrom: string,
  subject: string,
  unipassPrivateKey: string
): Promise<DkimParams> {
  const email = await getSignEmailWithDkim(
    subject,
    emailFrom,
    "test@unipass.id.com",
    unipassPrivateKey
  );
  const dkims = await DkimParams.parseEmailParams(email, []);

  return dkims;
}

export async function transferEth(from: Wallet, to: string, amount: BigNumber) {
  const ret = await (
    await from.sendTransaction({
      to,
      value: amount,
    })
  ).wait();

  return ret;
}
