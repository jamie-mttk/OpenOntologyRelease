# 多项式回归部署包

## 安装

```bash
pip install -r requirements.txt
```

## 本地自测

```bash
cd data/algorithm/polynomial-regression
python scripts/train.py --request fixtures/train-request.json --data fixtures/sample.csv --out ./out/
python scripts/invoke.py --request fixtures/invoke-request.json --out ./out-invoke/
```

将 `fixtures/invoke-request.json` 中 `artifact.dir` 改为 `./out` 的绝对路径。

## payload 约定

- `bindings`: `entity`, `target`, `features[]`
- `hyperparams`: `degree`, `includeBias`

## spec

见 `manifest.json`：`trainingConfig` / `trainingResult` / `invokeInput` / `invokeResult` 均在 `spec` 下。
