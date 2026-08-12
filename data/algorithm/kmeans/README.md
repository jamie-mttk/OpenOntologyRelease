# K-Means 聚类部署包

```bash
pip install -r requirements.txt
python scripts/train.py --request fixtures/train-request.json --data fixtures/sample.csv --out ./out/
python scripts/invoke.py --request fixtures/invoke-request.json --out ./out-invoke/
```

将 invoke-request 中 `artifact.dir` 指向 `./out` 绝对路径。
