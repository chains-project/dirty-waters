const fs = require('fs');
const path = require('path');
const lockfile = require('@yarnpkg/lockfile');

// yarn.lock文件路径
const yarnLockPath = path.resolve(__dirname, 'yarn.lock');
// 读取yarn.lock文件的内容
const yarnLockContent = fs.readFileSync(yarnLockPath, 'utf8');

// 解析yarn.lock文件
let json = lockfile.parse(yarnLockContent);

if (json.type === 'success') {
  // 提取所有依赖项名称和版本
  let dependencies = {};
  for (let key in json.object) {
    let pkg = key.substring(0, key.lastIndexOf('@'));
    let version = json.object[key].version;
    dependencies[pkg] = version;
  }

  // 将依赖项列表保存到文件
  const outputFile = path.resolve(__dirname, 'dependencies.json');
  fs.writeFileSync(outputFile, JSON.stringify(dependencies, null, 2), 'utf8');
  console.log(`Dependencies have been saved to ${outputFile}`);
} else {
  console.error('Failed to parse yarn.lock');
}