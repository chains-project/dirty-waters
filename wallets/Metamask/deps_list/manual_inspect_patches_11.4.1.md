patches format
- package name: @babel/runtime@patch
- for which version: @babel/runtime@npm%3A7.23.2
- patch path: #~/.yarn/patches/@babel-runtime-npm-7.23.2-d013d6cf7e.patch
- metadata(for integrity): ::version=7.23.2&hash=7df10d 

Inspection:

In .yarn/patches but didn't find in dep list:

1. patches/@formatjs-intl-utils-npm-3.3.1-08510c16ad.patch
2. patches/@keystonehq-bc-ur-registry-npm-0.5.0-alpha.5-b95c7992a6.patch
3. patches/@lavamoat-lavapack-npm-3.1.0-34c65d233b.patch
4. patches/fast-json-patch-npm-2.2.1-63b021bb37.patch
5. patches/request-npm-2.88.2-f4a57c72c4.patch
6. patches/web3-npm-0.20.7-ee7ef00c57.patch


In dep list but didn't find in ./yarn/patches
- fsevents@patch:fsevents@npm%3A1.2.9#optional!builtin<compat/fsevents>::version=1.2.9&hash=d11327
- fsevents@patch:fsevents@npm%3A2.3.2#optional!builtin<compat/fsevents>::version=2.3.2&hash=df0bf1
- resolve@patch:resolve@npm%3A1.22.3#optional!builtin<compat/resolve>::version=1.22.3&hash=c3c19d
- resolve@patch:resolve@npm%3A2.0.0-next.4#optional!builtin<compat/resolve>::version=2.0.0-next.4&hash=c3c19d
- typescript@patch:typescript@npm%3A3.9.10#optional!builtin<compat/typescript>::version=3.9.10&hash=3bd3d3
- typescript@patch:typescript@npm%3A4.5.5#optional!builtin<compat/typescript>::version=4.5.5&hash=bcec9a
- typescript@patch:typescript@npm%3A4.9.5#optional!builtin<compat/typescript>::version=4.9.5&hash=289587
- typescript@patch:typescript@npm%3A5.1.3#optional!builtin<compat/typescript>::version=5.1.3&hash=5da071

Who and why

Why
- make small changes to a dependency

Who:

`git log --pretty=format:'%an <%ae>' -- .yarn/patches  | sort | uniq -c | sort -nr`

- 5 legobeat <109787230+legobeat@users.noreply.github.com>
- 5 Brad Decker <bhdecker84@gmail.com>
- 4 Michele Esposito <34438276+mikesposito@users.noreply.github.com>

after Yarn v3: https://github.com/MetaMask/metamask-extension/tree/develop/.yarn/patches

before Yarn v3: https://github.com/MetaMask/metamask-extension/tree/c024d17f82da6135fb3913a03d0d4de5ac43a5c9/patches