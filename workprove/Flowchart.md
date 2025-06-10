```mermaid
graph TD
    A[导入相关数据集] --> B[加载预训练模型YOLOv8n.pt]
    B --> C[配置数据集文件data.yaml]
    C --> D[设置训练参数epochs=150, batch=4, optimizer=SGD]
    D --> E[开始模型训练]
    E --> F[保存训练好的模型]
```
