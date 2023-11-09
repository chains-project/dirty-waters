import {
  BigNumber,
  constants,
  Contract,
  ContractFactory,
  Overrides,
  providers,
  utils,
  Wallet,
} from "ethers";
import {
  formatBytes32String,
  hexlify,
  Interface,
  randomBytes,
  toUtf8Bytes,
} from "ethers/lib/utils";
import * as dotenv from "dotenv";

import ModuleMainArtifact from "../../../artifacts/unipass-wallet-contracts/contracts/modules/ModuleMain.sol/ModuleMain.json";
import ModuleMainUpgradableArtifact from "../../../artifacts/unipass-wallet-contracts/contracts/modules/ModuleMainUpgradable.sol/ModuleMainUpgradable.json";
import DkimKeysArtifact from "../../../artifacts/unipass-wallet-contracts/contracts/DkimKeys.sol/DkimKeys.json";
import WhiteListArtifact from "../../../artifacts/unipass-wallet-contracts/contracts/modules/commons/ModuleWhiteList.sol/ModuleWhiteList.json";
import TestERC20Artifact from "../../../artifacts/contracts/tests/TestERC20.sol/TestERC20.json";
import GreeterArtifact from "../../../artifacts/contracts/tests/Greeter.sol/Greeter.json";
import {
  CallTxBuilder,
  UpdateKeysetHashTxBuilder,
  UpdateKeysetHashWithTimeLockTxBuilder,
  UpdateTimeLockDuringTxBuilder,
} from "../src/transactionBuilder";
import {
  generateDkimParams,
  getKeysetHash,
  optimalGasLimit,
  randomKeys,
  Role,
  selectKeys,
  transferEth,
} from "./utils/common";
import { KeyBase, SignType } from "../src/key";
import { SessionKey } from "../src";
import { TxExcutor } from "../src/txExecutor";
import { pureEmailHash } from "unipass-wallet-dkim-base";
import { Deployer } from "../src/deployer";
import { UnlockKeysetHashTxBuilder } from "../src/transactionBuilder/unlockKeysetHashTxBuilder";
import { CancelLockKeysetHashTxBuilder } from "../src/transactionBuilder/cancelLockKeysetHashTxBuilder";
import { UpdateImplementationTxBuilder } from "../src/transactionBuilder/updateImplementationTxBuilder";
import NodeRSA from "node-rsa";
import { SyncAccountTxBuilder } from "../src/transactionBuilder/syncAccountTxBuilder";
import { randomInt } from "crypto";

describe("Test ModuleMain", () => {
  let moduleMainUpgradable: Contract;
  let ModuleMainUpgradable: ContractFactory;
  let moduleMain: Contract;
  let ModuleMain: ContractFactory;
  let provider: providers.JsonRpcProvider;
  let deployer: Deployer;
  let txParams: Overrides;
  let proxyModuleMain: Contract;
  let dkimKeys: Contract;
  let keysetHash: string;
  let keys: KeyBase[];
  let dkimKeysAdmin: Wallet;
  let whiteListAdmin: Wallet;
  let whiteList: Contract;
  let chainId: number;
  let TestERC20Token: ContractFactory;
  let testERC20Token: Contract;
  let JsonRpcNode;
  let unipassPrivateKey;
  let nonce: number;
  let metaNonce: number;
  beforeAll(async () => {
    dotenv.config({ path: `${__dirname}/../../../.env` });
    JsonRpcNode = process.env.JSON_RPC_NODE;
    const privateKey = new NodeRSA({ b: 2048 });
    unipassPrivateKey = privateKey.exportKey("pkcs1");
    provider = new providers.JsonRpcProvider(JsonRpcNode);
    chainId = (await provider.getNetwork()).chainId;
    const signer = provider.getSigner();

    deployer = await new Deployer(signer).init();
    const DkimKeys = new ContractFactory(
      new Interface(DkimKeysArtifact.abi),
      DkimKeysArtifact.bytecode,
      provider.getSigner()
    );
    txParams = {
      gasLimit: 10000000,
      gasPrice: (await signer.getGasPrice()).mul(12).div(10),
    };
    const instance = 0;

    dkimKeysAdmin = Wallet.createRandom().connect(provider);
    dkimKeys = await deployer.deployContract(
      DkimKeys,
      instance,
      txParams,
      dkimKeysAdmin.address
    );

    const WhiteList = new ContractFactory(
      new Interface(WhiteListArtifact.abi),
      WhiteListArtifact.bytecode,
      provider.getSigner()
    );
    whiteListAdmin = Wallet.createRandom().connect(provider);
    whiteList = await deployer.deployContract(
      WhiteList,
      instance,
      txParams,
      whiteListAdmin.address
    );

    const keyServer = utils.solidityPack(
      ["bytes32", "bytes32"],
      [formatBytes32String("s2055"), formatBytes32String("unipass.com")]
    );

    await transferEth(
      new Wallet(process.env.HARDHAT_PRIVATE_KEY, provider),
      dkimKeysAdmin.address,
      utils.parseEther("10")
    );
    let ret = await (
      await dkimKeys
        .connect(dkimKeysAdmin)
        .updateDKIMKey(
          keyServer,
          privateKey.exportKey("components-public").n.subarray(1)
        )
    ).wait();
    expect(ret.status).toEqual(1);
    await transferEth(
      new Wallet(process.env.HARDHAT_PRIVATE_KEY, provider),
      whiteListAdmin.address,
      utils.parseEther("10")
    );
    ModuleMainUpgradable = new ContractFactory(
      new Interface(ModuleMainUpgradableArtifact.abi),
      ModuleMainUpgradableArtifact.bytecode,
      provider.getSigner()
    );
    moduleMainUpgradable = await deployer.deployContract(
      ModuleMainUpgradable,
      instance,
      txParams,
      dkimKeys.address,
      whiteList.address
    );
    ret = await (
      await whiteList
        .connect(whiteListAdmin)
        .updateImplementationWhiteList(moduleMainUpgradable.address, true)
    ).wait();

    expect(ret.status).toEqual(1);
    ModuleMain = new ContractFactory(
      new Interface(ModuleMainArtifact.abi),
      ModuleMainArtifact.bytecode,
      provider.getSigner()
    );
    moduleMain = await deployer.deployContract(
      ModuleMain,
      instance,
      txParams,
      deployer.singleFactoryContract.address,
      moduleMainUpgradable.address,
      dkimKeys.address,
      whiteList.address
    );
    TestERC20Token = new ContractFactory(
      new Interface(TestERC20Artifact.abi),
      TestERC20Artifact.bytecode,
      provider.getSigner()
    );
  });
  beforeEach(async () => {
    testERC20Token = await TestERC20Token.deploy();

    keys = randomKeys(10);
    keysetHash = getKeysetHash(keys);

    proxyModuleMain = await deployer.deployProxyContract(
      moduleMain.interface,
      moduleMain.address,
      keysetHash,
      txParams
    );
    const txRet = await provider.getSigner().sendTransaction({
      to: proxyModuleMain.address,
      value: utils.parseEther("100"),
    });
    expect((await txRet.wait()).status).toEqual(1);
    const ret = await (
      await testERC20Token.mint(proxyModuleMain.address, 100)
    ).wait();
    expect(ret.status).toEqual(1);
    expect(await testERC20Token.balanceOf(proxyModuleMain.address)).toEqual(
      BigNumber.from(100)
    );
    nonce = 1;
    metaNonce = 1;
  });
  it("Updating KeysetHash Wighout TimeLock Should Success", async () => {
    const newKeysetHash = randomBytes(32);
    const txBuilder = await new UpdateKeysetHashTxBuilder(
      proxyModuleMain.address,
      metaNonce,
      newKeysetHash
    );
    const selectedKeys = await selectKeys(
      keys,
      txBuilder.digestMessage(),
      unipassPrivateKey,
      Role.Owner,
      100
    );
    const tx = (await txBuilder.generateSignature(selectedKeys)).build();

    const txExecutor = await new TxExcutor(chainId, proxyModuleMain, nonce, [
      tx,
    ]).generateSignature([]);
    const ret = await (
      await txExecutor.execute({ gasLimit: optimalGasLimit })
    ).wait();
    expect(ret.status).toEqual(1);
    expect(await proxyModuleMain.getKeysetHash()).toEqual(
      hexlify(newKeysetHash)
    );
    metaNonce++;
    nonce++;
  });

  it("Updating KeysetHash With TimeLock Should Success", async () => {
    const newKeysetHash = Buffer.from(randomBytes(32));

    const txBuilder = await new UpdateKeysetHashWithTimeLockTxBuilder(
      proxyModuleMain.address,
      metaNonce,
      newKeysetHash
    );

    const subject = txBuilder.digestMessage();
    const selectedKeys: [KeyBase, boolean][] = await selectKeys(
      keys,
      subject,
      unipassPrivateKey,
      Role.Guardian,
      50
    );
    const tx = (await txBuilder.generateSignature(selectedKeys)).build();
    const txExecutor = await new TxExcutor(chainId, proxyModuleMain, nonce, [
      tx,
    ]).generateSignature([]);
    const ret = await (
      await txExecutor.execute({ gasLimit: optimalGasLimit })
    ).wait();
    expect(ret.status).toEqual(1);
    const lockInfo = await proxyModuleMain.getLockInfo();
    expect(lockInfo.lockedKeysetHashRet).toEqual(
      `0x${newKeysetHash.toString("hex")}`
    );
    metaNonce++;
    nonce++;
  });

  it("Transfer ERC20 Should Success", async () => {
    const data = testERC20Token.interface.encodeFunctionData("transfer", [
      dkimKeysAdmin.address,
      10,
    ]);
    const tx = new CallTxBuilder(
      constants.Zero,
      testERC20Token.address,
      constants.Zero,
      data
    ).build();

    let sessionKey = new SessionKey(
      Wallet.createRandom(),
      SignType.EthSign,
      chainId,
      proxyModuleMain.address
    );
    const timestamp = Math.ceil(Date.now() / 1000) + 5000;
    const weight = 100;

    const selectedKeys: [KeyBase, boolean][] = await selectKeys(
      keys,
      sessionKey.digestPermitMessage(timestamp, weight),
      unipassPrivateKey,
      Role.AssetsOp,
      100
    );

    sessionKey = await sessionKey.generatePermit(
      timestamp,
      weight,
      selectedKeys
    );

    const txExecutor = new TxExcutor(chainId, proxyModuleMain, nonce, [tx]);

    const ret = await (
      await (
        await txExecutor.generateSignature(sessionKey)
      ).execute({ gasLimit: optimalGasLimit })
    ).wait();
    expect(ret.status).toEqual(1);
    expect(await testERC20Token.balanceOf(dkimKeysAdmin.address)).toEqual(
      BigNumber.from(10)
    );
    nonce++;
  });
  it("Transfer ETH Should Success", async () => {
    const to = Wallet.createRandom();
    const tx = new CallTxBuilder(
      constants.Zero,
      to.address,
      utils.parseEther("10"),
      "0x"
    ).build();
    let sessionKey = new SessionKey(
      Wallet.createRandom(),
      SignType.EthSign,
      chainId,
      proxyModuleMain.address
    );

    const timestamp = Math.ceil(Date.now() / 1000) + 5000;
    const weight = 100;

    const txExecutor = new TxExcutor(chainId, proxyModuleMain, nonce, [tx]);
    const subject = sessionKey.digestPermitMessage(timestamp, weight);
    const selectedKeys: [KeyBase, boolean][] = await selectKeys(
      keys,
      subject,
      unipassPrivateKey,
      Role.AssetsOp,
      100
    );

    sessionKey = await sessionKey.generatePermit(
      timestamp,
      weight,
      selectedKeys
    );
    const ret = await (
      await (
        await txExecutor.generateSignature(sessionKey)
      ).execute({ gasLimit: optimalGasLimit })
    ).wait();
    expect(ret.status).toEqual(1);
    expect(
      Number.parseInt(
        utils.formatEther(await provider.getBalance(to.address)),
        10
      )
    ).toEqual(10);
    nonce++;
  });
  it("Dkim Verify Should Success", async function () {
    const subject = constants.HashZero;
    const emailFrom = `${Buffer.from(randomBytes(10)).toString(
      "hex"
    )}@unipass.com`;
    const email = await generateDkimParams(
      emailFrom,
      subject,
      unipassPrivateKey
    );
    const pepper = hexlify(randomBytes(32));
    const ret = await dkimKeys.dkimVerify(email.serialize(), 0, pepper);
    expect(ret[0]).toBe(true);
    expect(ret[1]).toBe(pureEmailHash(emailFrom, pepper));
    expect(ret[2]).toBe(hexlify(toUtf8Bytes(subject)));
  });
  it("Update TimeLock During Should Success", async () => {
    const newDelay = 3600;
    const txBuilder = new UpdateTimeLockDuringTxBuilder(
      proxyModuleMain.address,
      metaNonce,
      newDelay
    );
    const subject = txBuilder.digestMessage();
    const selectedKeys: [KeyBase, boolean][] = await selectKeys(
      keys,
      subject,
      unipassPrivateKey,
      Role.Owner,
      100
    );
    const tx = (await txBuilder.generateSignature(selectedKeys)).build();
    const ret = await (
      await (
        await new TxExcutor(chainId, proxyModuleMain, nonce, [
          tx,
        ]).generateSignature([])
      ).execute(txParams)
    ).wait();

    expect(ret.status).toBe(1);
    const lockInfo = await proxyModuleMain.getLockInfo();
    expect(lockInfo.lockDuringRet).toEqual(newDelay);
  });
  it("Unlock KeysetHash TimeLock Should Success", async () => {
    // Step 1: Update TimeLock During
    const newTimelockDuring = 3;
    const txBuilder1 = new UpdateTimeLockDuringTxBuilder(
      proxyModuleMain.address,
      metaNonce,
      newTimelockDuring
    );
    let subject = txBuilder1.digestMessage();
    let selectedKeys: [KeyBase, boolean][] = await selectKeys(
      keys,
      subject,
      unipassPrivateKey,
      Role.Owner,
      100
    );
    let tx = (await txBuilder1.generateSignature(selectedKeys)).build();
    let ret = await await (
      await (
        await new TxExcutor(chainId, proxyModuleMain, nonce, [
          tx,
        ]).generateSignature([])
      ).execute(txParams)
    ).wait();

    expect(ret.status).toBe(1);
    let lockInfo = await proxyModuleMain.getLockInfo();
    expect(lockInfo.lockDuringRet).toEqual(newTimelockDuring);
    metaNonce++;
    nonce++;

    // Step 2: Update KeysetHash
    const newKeysetHash = Buffer.from(randomBytes(32));
    const txBuilder2 = new UpdateKeysetHashWithTimeLockTxBuilder(
      proxyModuleMain.address,
      metaNonce,
      newKeysetHash
    );
    subject = txBuilder2.digestMessage();
    selectedKeys = await selectKeys(
      keys,
      subject,
      unipassPrivateKey,
      Role.Guardian,
      50
    );
    tx = (await txBuilder2.generateSignature(selectedKeys)).build();
    let txExecutor = await new TxExcutor(chainId, proxyModuleMain, nonce, [
      tx,
    ]).generateSignature([]);
    ret = await (
      await txExecutor.execute({ gasLimit: optimalGasLimit })
    ).wait();
    expect(ret.status).toEqual(1);
    lockInfo = await proxyModuleMain.getLockInfo();
    expect(lockInfo.lockedKeysetHashRet).toEqual(
      `0x${newKeysetHash.toString("hex")}`
    );
    metaNonce++;
    nonce++;

    // Step3 Unlock TimeLock
    tx = new UnlockKeysetHashTxBuilder(
      proxyModuleMain.address,
      metaNonce
    ).build();
    txExecutor = await new TxExcutor(chainId, proxyModuleMain, nonce, [
      tx,
    ]).generateSignature([]);

    try {
      await txExecutor.execute({ gasLimit: optimalGasLimit });
    } catch (error) {
      expect(JSON.parse(error.body).error.message).toEqual(
        `Error: VM Exception while processing transaction: reverted with custom error 'TxFailed("${txExecutor.digestMessage()}", "0x08c379a00000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000001e5f72657175697265546f556e4c6f636b3a20554e4c4f434b5f41465445520000")'`
      );
    }

    await new Promise((resolve) =>
      // eslint-disable-next-line no-promise-executor-return
      setTimeout(resolve, newTimelockDuring * 1000 + 1000)
    );

    ret = await (
      await txExecutor.execute({ gasLimit: optimalGasLimit })
    ).wait();
    expect(ret.status).toEqual(1);
    lockInfo = await proxyModuleMain.getLockInfo();
    expect(lockInfo.isLockedRet).toBe(false);
    expect(await proxyModuleMain.getKeysetHash()).toEqual(
      hexlify(newKeysetHash)
    );
  });

  it("Cancel KeysetHash TimeLock Should Success", async () => {
    // Step 1: Update KeysetHash
    const newKeysetHash = Buffer.from(randomBytes(32));
    const txBuilder1 = new UpdateKeysetHashWithTimeLockTxBuilder(
      proxyModuleMain.address,
      metaNonce,
      newKeysetHash
    );
    let subject = txBuilder1.digestMessage();
    let selectedKeys: [KeyBase, boolean][] = await selectKeys(
      keys,
      subject,
      unipassPrivateKey,
      Role.Guardian,
      50
    );
    let tx = (await txBuilder1.generateSignature(selectedKeys)).build();
    let txExecutor = await new TxExcutor(chainId, proxyModuleMain, nonce, [
      tx,
    ]).generateSignature([]);
    let ret = await (
      await txExecutor.execute({ gasLimit: optimalGasLimit })
    ).wait();
    expect(ret.status).toEqual(1);
    let lockInfo = await proxyModuleMain.getLockInfo();
    expect(lockInfo.lockedKeysetHashRet).toEqual(
      `0x${newKeysetHash.toString("hex")}`
    );
    metaNonce++;
    nonce++;

    // Step 2: Cancel TimeLock
    const txBuilder2 = await new CancelLockKeysetHashTxBuilder(
      proxyModuleMain.address,
      metaNonce
    );
    subject = txBuilder2.digestMessage();
    selectedKeys = await selectKeys(
      keys,
      subject,
      unipassPrivateKey,
      Role.Owner,
      1
    );
    tx = (await txBuilder2.generateSignature(selectedKeys)).build();

    txExecutor = await new TxExcutor(chainId, proxyModuleMain, nonce, [
      tx,
    ]).generateSignature([]);

    ret = await (
      await txExecutor.execute({ gasLimit: optimalGasLimit })
    ).wait();
    expect(ret.status).toEqual(1);
    lockInfo = await proxyModuleMain.getLockInfo();
    expect(lockInfo.isLockedRet).toBe(false);
    expect(await proxyModuleMain.getKeysetHash()).toEqual(constants.HashZero);
  });

  it("Update Implemenation Should Success", async () => {
    const Greeter = new ContractFactory(
      new Interface(GreeterArtifact.abi),
      GreeterArtifact.bytecode
    );
    const greeter = await deployer.deployContract(Greeter, 0, txParams);

    let ret = await (
      await whiteList
        .connect(whiteListAdmin)
        .updateImplementationWhiteList(greeter.address, true)
    ).wait();

    expect(ret.status).toEqual(1);

    const txBuilder = new UpdateImplementationTxBuilder(
      proxyModuleMain.address,
      metaNonce,
      greeter.address
    );
    const subject = txBuilder.digestMessage();
    const selectedKeys: [KeyBase, boolean][] = await selectKeys(
      keys,
      subject,
      unipassPrivateKey,
      Role.Owner,
      100
    );

    const tx = (await txBuilder.generateSignature(selectedKeys)).build();
    const txExecutor = await new TxExcutor(chainId, proxyModuleMain, nonce, [
      tx,
    ]).generateSignature([]);
    ret = await (
      await txExecutor.execute({ gasLimit: optimalGasLimit })
    ).wait();
    expect(ret.status).toEqual(1);
    proxyModuleMain = greeter.attach(proxyModuleMain.address);
    expect(await proxyModuleMain.ret1()).toEqual(BigNumber.from(1));
    metaNonce++;
    nonce++;
  });

  it("Sync Account Should Success", async () => {
    const newKeysetHash = Buffer.from(randomBytes(32));
    const newTimelockDuring = randomInt(100);
    const newImplementation = moduleMainUpgradable.address;
    metaNonce = 10;
    const txBuilder = new SyncAccountTxBuilder(
      proxyModuleMain.address,
      metaNonce,
      newKeysetHash,
      newTimelockDuring,
      newImplementation
    );
    const subject = txBuilder.digestMessage();
    const selectedKeys = await selectKeys(
      keys,
      subject,
      unipassPrivateKey,
      Role.Owner,
      100
    );
    const tx = (await txBuilder.generateSignature(selectedKeys)).build();
    const txExecutor = await new TxExcutor(chainId, proxyModuleMain, nonce, [
      tx,
    ]).generateSignature([]);
    const ret = await (
      await txExecutor.execute({ gasLimit: optimalGasLimit })
    ).wait();
    expect(ret.status).toEqual(1);
    expect(await proxyModuleMain.getKeysetHash()).toEqual(
      `0x${newKeysetHash.toString("hex")}`
    );
    expect(await proxyModuleMain.getMetaNonce()).toEqual(
      BigNumber.from(metaNonce)
    );
    expect(await proxyModuleMain.getImplementation()).toEqual(
      newImplementation
    );
    const lockInfo = await proxyModuleMain.getLockInfo();
    expect(lockInfo.lockDuringRet).toEqual(newTimelockDuring);
    metaNonce++;
    nonce++;
  });
});
