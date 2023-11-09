# Unipass-Wallet.js

## Install

```typescript
npm i unipass-wallet
```

## Packages

```text
 --- packages
|
|------ unipass-wallet-abi
|
|------ unipass-wallet-dkim-base
|
|------ unipass-wallet-dkim
|
 ------ unipass-wallet
```

## Transaction Builder

```typescript
// Update KeysetHash
const txBuilder = new UpdateKeysetHashTxBuilder(
  userAddr,
  metaNonce,
  newKeysetHash
);

// Unlock KeysetHash TimeLock
const txBuilder = new UnlockKeysetHashTxBuilder(userAddr, metaNonce);

// Cancel KeysetHash TimeLock
const txBuilder = new CancelLockKeysetHashTxBuilder(userAddr, metaNonce);

// Update TimeLock During
const txBuilder = new UpdateTimeLockDuringTxBuilder(
  userAddr,
  metaNonce,
  newTimeLockDuring
);

// Update Implemenation
const txBuilder = new UpdateImplementationTxBuilder(
  userAddr,
  metaNonce,
  newImplemenation
);
```

## Build Transaction

```typescript
const tx = (await txBuilder.generateSignature(toSignedKeys)).build();
```

## Tx Executor

```typescript
const txExecutor = await new TxExcutor(
  chainId,
  1,
  [tx],
  ethers.constants.AddressZero,
  ethers.constants.Zero,
  ethers.constants.AddressZero
).generateSigBySessionKey(sessionKeySigGenerator, SignType.EthSign);

# Tx Execute
const ret = await (
  await txExecutor.execute(proxyModuleMain, optimalGasLimit)
).wait();
```

## Publish

```shell
pnpm changeset
pnpm changeset version
```
