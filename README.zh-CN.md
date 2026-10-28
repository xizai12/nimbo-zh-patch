# Nimbo 简体中文补丁（非官方）

[English](README.md) | 简体中文

将已验证的 macOS Nimbo 原版复制并汉化为独立的 `.app`，原版不会被修改。这是**更新后重新运行的补丁工具，不是插件或自动更新服务**。只接受与已核对发行物逐字节匹配的 0.6.2/0.6.3；未来版本必须重新验证并添加支持，不能保证自动兼容。

本仓库**不提供 Nimbo 原程序、图标、安装包、解压后的前端源码或签名**。Nimbo 的权利归原作者所有。本仓库的 MIT 许可仅覆盖此处的补丁代码和中文译文，与 Nimbo 官方无关。

## 支持范围

| Nimbo 版本 | 平台 | 验证状态 |
| --- | --- | --- |
| 0.6.2 | macOS 通用版 | 本机原版哈希、两架构资源静态验证 |
| 0.6.3 | macOS 通用版 | [官方发布归档](https://github.com/EmilMoe/binaries/releases/tag/nimbo-v0.6.3)及两架构资源静态验证 |

510 项前端词条翻译为简体中文，原生菜单和部分文件种类名称仍为英文。默认使用中文；若之前保存了英文偏好，可以在应用设置的语言选项中选“简体中文”。尚未在隔离账号中完成界面及 S3 连接测试。

## 安装与配置

需要 macOS、Python 3.10+、Node.js 18+ 和 Git。`node` 用于检查修改后的 JavaScript 语法，**不会执行它**。

```bash
git clone https://github.com/xizai12/nimbo-zh-patch.git
cd nimbo-zh-patch
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
node --version
```

先用**未修改的** Nimbo 原版做校验，不会在 dry-run 中写出应用：

```bash
python patch_nimbo.py --source '/Applications/Nimbo.app' --dry-run
python patch_nimbo.py --source '/Applications/Nimbo.app'
```

第二条命令默认在此仓库目录生成 `Nimbo 中文 <版本>.app`。实际以原版版本为准；例如本机原版是 0.6.2，命令只会生成 0.6.2 中文副本，**不会自动下载 0.6.3**。源程序、译文、两架构的嵌入资源、图标和 `Info.plist` 必须通过哈希/结构校验；有一项不符就停止。输出只能放在此仓库目录或其子目录的**新** `.app` 路径，不会覆盖已有副本，也不允许原地修改或写入 `/Applications`。

如需自定义名称，指定仓库内的绝对路径。应用内部显示名会与输出文件名一致：

```bash
python patch_nimbo.py --source '/Applications/Nimbo.app' \
  --output "$PWD/Nimbo.app"
```

这只会在**仓库目录内**生成一个同名的独立副本，不会删除或替换 `/Applications` 中的原版。先在独立 macOS 用户账号下用测试凭据评估，再考虑替换原版；务必保留可用于回退的原版备份。

### 从官方 0.6.3 归档生成

从[官方 0.6.3 发布页](https://github.com/EmilMoe/binaries/releases/tag/nimbo-v0.6.3)下载 macOS 的 `Nimbo.app.tar.gz` 到 `~/Downloads`。该归档已核对的 SHA-256 是：

```text
86098243bf0f6cf5a098020c3c9cb24ed771d35c5a77c0384d383968ea9265fe
```

**先核对**本地下载的哈希，再解压到独立目录并引用里面的原版应用：

```bash
shasum -a 256 "$HOME/Downloads/Nimbo.app.tar.gz"
mkdir -p "$HOME/Downloads/nimbo-0.6.3-original"
tar -xzf "$HOME/Downloads/Nimbo.app.tar.gz" -C "$HOME/Downloads/nimbo-0.6.3-original"
python patch_nimbo.py --source "$HOME/Downloads/nimbo-0.6.3-original/Nimbo.app" --dry-run
python patch_nimbo.py --source "$HOME/Downloads/nimbo-0.6.3-original/Nimbo.app"
```

若下载文件哈希不等于上面的值，**不要解压或运行它**。这些命令不安装原版或生成的副本到 `/Applications`。

### 修改中文词条

编辑 [zh.json](zh.json)，保留全部 510 个键、列表长度与 `{name}` 等占位符。再次运行 dry-run 检查；文字过长导致压缩资源无法装入原槽位时，工具会拒绝生成。已有 `.app` 不会被自动更新，修改译文后需为新副本另取 `--output` 名称。

## 更新、风险与回退

- Nimbo 官方更新不会保留补丁。对**新的干净原版**重新运行本工具；未知版本会拒绝。维护者必须单独核实发行物、两架构偏移、词条与哈希后才能添加支持。不要把旧中文副本作为原版输入。
- 修改后的程序**未签名、未公证**，macOS 可能拒绝启动。不要为了运行它而全局关闭系统安全功能或批量移除隔离属性。
- 副本保留原版 bundle ID，可能与原版共享本机偏好和 S3 凭据。请仅在**独立 macOS 用户账号**及测试凭据下评估；目前不建议用它连接真实 S3 账号。
- 补丁移除了启动时自动检查更新的调用，**没有**全面禁用手动更新界面；不要通过中文副本执行应用内更新。
- 回退只需停止使用中文副本、继续运行原版。不要因为回退而删除或迁移共享应用数据。生成的副本位于仓库目录，仓库已忽略 `.app` 文件以防误提交。

不执行进程注入、不安装定时任务、不自动下载更新。运行单元测试：`python -m unittest discover -s tests -v`。未提交上游二进制，因此完整集成测试需自备经过核对的官方原版，再运行 `--dry-run`。
