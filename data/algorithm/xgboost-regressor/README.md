# XGBoost 回归部署包

```bash
pip install -r requirements.txt
python scripts/train.py --request fixtures/train-request.json --data fixtures/sample.csv --out ./out/
```

将 `fixtures/invoke-request.json` 的 `artifact.dir` 设为 `./out` 绝对路径后：

```bash
python scripts/invoke.py --request fixtures/invoke-request.json --out ./out-invoke/
```
